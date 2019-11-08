# Copyright 2016 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONnice_date_timeS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import time
from adapt.intent import IntentBuilder
from os.path import dirname, join
from datetime import datetime, timedelta
from mycroft import MycroftSkill,  intent_handler, intent_file_handler
from mycroft.util.parse import extract_datetime, extract_number, normalize
from mycroft.util.time import now_local, to_local, to_utc, now_utc
from mycroft.util.format import nice_time, nice_date, nice_date_time
from mycroft.util.log import LOG
from mycroft.util import play_wav
import re

REMINDER_PING = join(dirname(__file__), 'twoBeep.wav')

MINUTES = 60  # seconds


def deserialize(dt):
    return datetime.strptime(dt, '%Y%d%m-%H%M%S-%z')


def serialize(dt):
    return dt.strftime('%Y%d%m-%H%M%S-%z')


def is_today(d):
    return d.date() == now_local().date()


def is_tomorrow(d):
    return d.date() == now_local().date() + timedelta(days=1)


def contains_datetime(datetime, lang='ar-sa'):
    return extract_datetime(datetime)


def is_affirmative(utterance, lang='ar-sa'):
    affirmatives = ['نعم', 'ايه', 'اكيد','اي']
    for word in affirmatives:
        if word in utterance:
            return True
    return False


class ReminderSkill(MycroftSkill):
    def __init__(self):
        super(ReminderSkill, self).__init__()
        self.notes = {}
        self.primed = False

        self.cancellable = []  # list of reminders that can be cancelled
        self.NIGHT_HOURS = [23, 0, 1, 2, 3, 4, 5, 6]

    def initialize(self):
        # Handlers for notifications after speak
        # TODO Make this work better in test
        from mycroft.messagebus.client.ws import WebsocketClient
        if isinstance(self.bus, WebsocketClient):
            self.add_event('speak', self.prime)
            self.add_event('mycroft.skill.handler.complete', self.notify)
            self.add_event('mycroft.skill.handler.start', self.reset)

        # Reminder checker event
        self.schedule_repeating_event(self.__check_reminder, datetime.now(),
                                      0.5 * MINUTES, name='reminder')

    def add_notification(self, identifier, note, expiry):
        self.notes[identifier] = (note, expiry)

    def prime(self, message):
        self.primed = True

    def reset(self, message):
        time.sleep(10)
        self.primed = False

    def notify(self, message):
        if self.name in message.data.get('name', ''):
            self.primed = False
            return

        handled_reminders = []
        now = now_local()
        if self.primed:
            for r in self.settings.get('reminders', []):
                print('Checking {}'.format(r))
                dt = deserialize(r[1])
                if now > dt - timedelta(minutes=10) and now < dt and \
                        r[0] not in self.cancellable:
                    handled_reminders.append(r)
                    self.speak_dialog('ByTheWay', data={'reminder': r[0]})
                    self.cancellable.append(r[0])

            self.primed = False

    def __check_reminder(self, message):
        """ Repeating event handler. Checking if a reminder time has been
            reached and presents the reminder. """
        now = now_local()
        handled_reminders = []
        for r in self.settings.get('reminders', []):
            dt = deserialize(r[1])
            if now > dt:
                play_wav(REMINDER_PING)
                self.speak_dialog('Reminding', data={'reminder': r[0]})
                handled_reminders.append(r)
            if now > dt - timedelta(minutes=10):
                self.add_notification(r[0], r[0], dt)
        self.remove_handled(handled_reminders)

    def remove_handled(self, handled_reminders):
        """ The reminder is removed and rescheduled to repeat in 2 minutes.

            It is also marked as "cancellable" allowing "cancel current
            reminder" to remove it.

            Repeats a maximum of 3 times.
        """
        for r in handled_reminders:
            if len(r) == 3:
                repeats = r[2] + 1
            else:
                repeats = 1
            self.settings['reminders'].remove(r)
            # If the reminer hasn't been repeated 3 times reschedule it
            if repeats < 3:
                self.speak_dialog('ToCancelInstructions')
                new_time = deserialize(r[1]) + timedelta(minutes=2)
                self.settings['reminders'].append(
                        (r[0], serialize(new_time), repeats))

                # Make the reminder cancellable
                if r[0] not in self.cancellable:
                    self.cancellable.append(r[0])
            else:
                # Do not schedule a repeat and remove the reminder from
                # the list of cancellable reminders
                self.cancellable = [c for c in self.cancellable if c != r[0]]

    def remove_by_name(self, name):
        for r in self.settings.get('reminders', []):
            if r[0] == name:
                break
        else:
            return False  # No matching reminders found
        self.settings['reminders'].remove(r)
        return True  # Matching reminder was found and removed

    def reschedule_by_name(self, name, new_time):
        """ Reschedule the reminder by it's name

            Arguments:
                name:       Name of reminder to reschedule.
                new_time:   New time for the reminder.

            Returns (Bool): True if a reminder was found.
        """
        serialized = serialize(new_time)
        for r in self.settings.get('reminders', []):
            if r[0] == name:
                break
        else:
            return False  # No matching reminders found
        self.settings['reminders'].remove(r)
        self.settings['reminders'].append((r[0], serialized))
        return True

    def date_str(self, d):
        if is_today(d):
            return 'اليوم'
        elif is_tomorrow(d):
            return 'بكره'
        else:
            return nice_date(d.date())

    @intent_handler(IntentBuilder("").require("ReminderAt").optionally("ReminderName").require("DateTime"))
    def add_new_reminder(self, msg):
        """ Handler for adding  a reminder with a name at a specific time. """
        

        reminder = msg.data.get("ReminderName")
        
        if reminder is None:
            return self.add_unnamed_reminder_at(msg)
            

        datetime = msg.data.get("DateTime")
        print(datetime)
          
        reminder_time,rest, DateType = extract_datetime(datetime, now_local(),
                                            self.lang)

        print(rest)
        print(serialize(reminder_time))
        if reminder_time.hour in self.NIGHT_HOURS:
            self.speak_dialog('ItIsNight')
            if not self.ask_yesno('AreYouSure')=='نعم':
                return # Don't add if user cancels


        self.__save_reminder_local(reminder, reminder_time, DateType)

    def __save_reminder_local(self, reminder, reminder_time, DateType):
        """ Speak verification and store the reminder. """
        # Choose dialog depending on the date
        
        self.speak_dialog('SavingReminder', {'timedate': nice_date_time(reminder_time, self.lang, now=now_local(), use_24hour=False,
                   use_ampm=True, DateType=DateType)})


        # Store reminder
        serialized = serialize(reminder_time)

        if 'reminders' in self.settings:
            self.settings['reminders'].append((reminder, serialized))
        else:
            self.settings['reminders'] = [(reminder, serialized)]

    def __save_unspecified_reminder(self, reminder):
        if 'unspec' in self.settings:
            self.settings['unspec'].append(reminder)
        else:
            self.settings['unspec'] = [reminder]

        self.speak_dialog('SavingReminderUnspec')

    @intent_handler(IntentBuilder("").require("ReminderAt").require("ReminderName").optionally("DateTime"))
    def add_unspecified_reminder(self, msg=None):
        """ Starts a dialog to add a reminder when no time was supplied
            for the reminder.
        """
        reminder = msg.data.get("ReminderName")
        # Handle the case where padatious misses the time/date
        if msg.data.get("DateTime") is not None:
            return self.add_new_reminder(msg)

        elif msg.data.get("DateTime") is None:
            response1 = self.get_response('ParticularTime')
            if response1 and is_affirmative(response1):
                # Get the time
                response2 = self.get_response('SpecifyTime')
                dt, rest, DateType = extract_datetime(response2)
                print(dt)
                if dt is not None:
                    self.speak('حسنا')
                    self.__save_reminder_local(reminder, dt, DateType)
            else:
                LOG.debug('put into general reminders')
                self.__save_unspecified_reminder(reminder)


    def add_unnamed_reminder_at(self, msg=None):
        """ Handles the case where a time was given but no reminder
            name was added.
        """

        utterance = msg.data.get("DateTime")
        reminder_time, _, DateType = extract_datetime(utterance, now_local(), self.lang)

        if msg.data.get("ReminderName") is None:

            response = self.get_response('AboutWhat')
            if response and reminder_time:
                self.__save_reminder_local(response, reminder_time, DateType)

    @intent_handler(IntentBuilder("").require("DeleteReminderForDay").require("Date"))
    def remove_reminders_for_day(self, msg=None):
        """ Remove all reminders for the specified date. """
        if msg.data.get("Date") is not None:
            date, _,_= extract_datetime(msg.data.get("Date"), lang=self.lang)

        date_str = self.date_str(date)
        # If no reminders exists for the provided date return;
        for r in self.settings['reminders']:
            if deserialize(r[1]).date() == date.date():
                break
        else:  # Let user know that no reminders were removed
            self.speak_dialog('NoRemindersForDate', {'date': msg.data.get("Date")})
            return

        if self.ask_yesno('ConfirmRemoveDay', data={'date': msg.data.get("Date")}) == 'نعم':
            if 'reminders' in self.settings:
                self.settings['reminders'] = [
                        r for r in self.settings['reminders']
                        if deserialize(r[1]).date() != date.date()]
                self.speak_dialog('ClearedAll')


    @intent_handler(IntentBuilder("").require("GetRemindersForDay").require("Date"))
    def get_reminders_for_day(self, msg=None):
        """ List all reminders for the specified date. """
        print("hello")
        if msg.data.get("Date") is not None:
            date, _,_ = extract_datetime(msg.data.get("Date"),now_local(), lang=self.lang)


        if 'reminders' in self.settings:
            reminders = [r for r in self.settings['reminders']
                         if deserialize(r[1]).date() == date.date()]
            if len(reminders) > 0:
                for r in reminders:
                    reminder, dt = (r[0], deserialize(r[1]))
                    self.speak(reminder +" "+ nice_time(dt))
                return
        self.speak_dialog('NoUpcoming')

    @intent_file_handler('GetNextReminders.intent')
    def get_next_reminder(self, msg=None):
        """ Get the first upcoming reminder. """
        if len(self.settings.get('reminders', [])) > 0:
            reminders = [(r[0], deserialize(r[1]))
                         for r in self.settings['reminders']]
            next_reminder = sorted(reminders, key=lambda tup: tup[1])[0]

            if is_today(next_reminder[1]):
                self.speak_dialog('NextToday',
                                  data={'time': nice_time(next_reminder[1]),
                                        'reminder': next_reminder[0]})
            elif is_tomorrow(next_reminder[1]):
                self.speak_dialog('NextTomorrow',
                                  data={'time': nice_time(next_reminder[1]),
                                        'reminder': next_reminder[0]})
            else:
                self.speak_dialog('NextOtherDate',
                                  data={'time': nice_time(next_reminder[1]),
                                        'date': nice_date(next_reminder[1]),
                                        'reminder': next_reminder[0]})
        else:
            self.speak_dialog('NoUpcoming')


    def __cancel_active(self):
        """ Cancel all active reminders. """
        remove_list = []
        ret = len(self.cancellable) > 0  # there were reminders to cancel
        for c in self.cancellable:
            if self.remove_by_name(c):
                remove_list.append(c)
        for c in remove_list:
            self.cancellable.remove(c)
        return ret

    @intent_file_handler('CancelActiveReminder.intent')
    def cancel_active(self, message):
        """ Cancel a reminder that's been triggered (and is repeating every
            2 minutes. """
        if self.__cancel_active():
            self.speak_dialog('ReminderCancelled')
        else:
            self.speak_dialog('NoActive')

    @intent_file_handler('SnoozeReminder.intent')
    def snooze_active(self, message):
        """ Snooze the triggered reminders for 15 minutes. """
        remove_list = []
        for c in self.cancellable:
            if self.reschedule_by_name(c,
                                       now_local() + timedelta(minutes=15)):
                self.speak_dialog('RemindingInFifteen')
                remove_list.append(c)
        for c in remove_list:
            self.cancellable.remove(c)

    @intent_file_handler('ClearReminders.intent')
    def clear_all(self, message):
        """ Clear all reminders. """
        if self.ask_yesno('ClearAll') == 'نعم':
            self.__cancel_active()
            self.settings['reminders'] = []
            self.speak_dialog('ClearedAll')

    def stop(self, message=None):
        if self.__cancel_active():
            self.speak_dialog('ReminderCancelled')
            return True
        else:
            return False


def create_skill():
    return ReminderSkill()
