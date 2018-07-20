# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


import time
from os.path import dirname, join
from datetime import datetime, timedelta
from parsedatetime import Calendar
from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.parse import extract_datetime, extract_number
from mycroft.util.time import now_local, to_local, to_utc, now_utc
from mycroft.util.format import nice_time
from mycroft.util.log import LOG
from mycroft.util import play_wav

REMINDER_PING = join(dirname(__file__), 'twoBeep.wav')

MINUTES = 60  # seconds


def local_epoch():
    "Localized time since epoch"
    return time.mktime(now_local().timetuple())

def contains_datetime(utterance, lang='en-us'):
    return extract_datetime(utterance)[1] != utterance


def is_affirmative(utterance, lang='en-us'):
    affirmatives = ['yes', 'sure', 'please do']
    for word in affirmatives:
        if word in utterance:
            return True
    return False

def prev_midnight(now=None):
    """ Returns preceding midnight.

    Arguments:
        now (datetime): Current time

    Returns: (datetime) time for previous midnight
    """
    now = now or now_local()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def next_midnight(now=None):
    """ Returns the upcoming midnight.

    Arguments:
        now (datetime): Current time

    Returns: (datetime) time for the next midnight
    """
    return prev_midnight(now) + timedelta(hours=24)


class ReminderSkill(MycroftSkill):
    def __init__(self):
        super(ReminderSkill, self).__init__()
        self.notes = {}
        self.primed = False

        self.cancellable = []  # list of reminders that can be cancelled

    def initialize(self):
        self.add_event('speak', self.prime)
        self.add_event('mycroft.skill.handler.complete', self.notify)
        self.add_event('mycroft.skill.handler.start', self.reset)

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
        LOG.info('notify: {}'.format(self.primed))
        handled_reminders = []
        now = local_epoch()
        if self.primed:
            for r in self.settings.get('reminders', []):
                print('Checking {}'.format(r))
                if now > r[1] - 600 and now < r[1] and \
                        r[0] not in self.cancellable:
                    handled_reminders.append(r)
                    self.speak_dialog('by.the.way', data={'reminder': r[0]})
                    self.cancellable.append(r[0])

            self.primed = False

    def __check_reminder(self, message):
        LOG.debug('Checking reminders')
        now = local_epoch()
        handled_reminders = []
        for r in self.settings.get('reminders', []):
            if now > r[1]:
                play_wav(REMINDER_PING)
                self.speak(r[0])
                handled_reminders.append(r)
            if now > r[1] - 600:
                self.add_notification(r[0], r[0], r[1])
        self.remove_handled(handled_reminders)

    def remove_handled(self, handled_reminders):
        for r in handled_reminders:
            self.settings['reminders'].remove(r)
            self.settings['reminders'].append((r[0], r[1] + 2 * MINUTES))
            if r[0] not in self.cancellable:
                self.cancellable.append(r[0])

    def remove_by_name(self, name):
        for r in self.settings.get('reminders', []):
            if r[0] == name:
                break
        else:
            return False  # No matching reminders found
        self.settings['reminders'].remove(r)
        return True  # Matching reminder was found and removed

    def reschedule_by_name(self, name, new_time):
        for r in self.settings.get('reminders', []):
            if r[0] == name:
                break
        else:
            return False  # No matching reminders found
        self.settings['reminders'].remove(r)
        self.settings['reminders'].append((r[0], new_time))
        return True

    @intent_file_handler('ReminderAt.intent')
    def add_new_reminder(self, msg=None):
        # mogrify the response
        reminder = msg.data.get('reminder', None)
        if reminder is None:
            return self.add_unnamed_reminder_at(msg)

        reminder = reminder.replace(' my ', ' your ')
        LOG.info('REMINDER: "{}"'.format(reminder))
        if 'timedate' in msg.data:
            utterance = msg.data['timedate']
        else:
            utterance = msg.data['utterance']
        reminder_time, rem = extract_datetime(utterance, now_local(),
                                              self.lang)
        LOG.info(reminder_time)
        self.primed = False
        if rem != utterance: # Nothing was extracted
            self.speak_dialog('SavingReminder',
                              {'timedate': nice_time(reminder_time)})

            self.__save_reminder_local(reminder, reminder_time)
        else:
            self.speak_dialog('NoDateTime')

    def __save_reminder_local(self, reminder, reminder_time):
        since_epoch = time.mktime(reminder_time.timetuple())
        LOG.info(since_epoch)
        if 'reminders' in self.settings:
            self.settings['reminders'].append((reminder, since_epoch))
        else:
            self.settings['reminders'] = [(reminder, since_epoch)]

    def __save_unspecified_reminder(self, reminder):
        if 'unspec' in self.settings:
            self.settings['unspec'].append(reminder)
        else:
            self.settings['unspec'] = [reminder]

    @intent_file_handler('Reminder.intent')
    def add_unspecified_reminder(self, msg=None):
        reminder = msg.data['reminder']
        if contains_datetime(msg.data['utterance']):
            return self.add_new_reminder(msg)

        response = self.get_response('ParticularTime')
        if is_affirmative(response):
            # Check if a time was also in the response
            dt = extract_datetime(response)
            if dt is None:
                # No time found in the response
                response = self.get_response('SpecifyTime')
                dt = extract_datetime(response)
                if not dt:
                    self.speak('Fine, be that way')
                    return

            self.__save_reminder_local(reminder, dt)
            self.speak_dialog('SavingReminder',
                              {'timedate': nice_time(dt)})
        else:
            LOG.debug('put into general reminders')
            self.__save_unspecified_reminder(reminder)

    @intent_file_handler('UnspecifiedReminderAt.intent')
    def add_unnamed_reminder_at(self, msg=None):
        utterance = msg.data['timedate']
        reminder_time = extract_datetime(utterance, now_local(), self.lang)
        response = self.get_response('AboutWhat')
        if response and reminder_time:
            self.__save_reminder_local(response, reminder_time)
            self.speak_dialog('SavingReminder',
                              {'timedate': nice_time(reminder_time)})

    @intent_file_handler('DeleteReminderForDay.intent')
    def remove_reminders_for_day(self, msg=None):
        if 'date' in msg.data:
            date, _ = extract_datetime(msg.data['date'], lang=self.lang)
        else:
            date, _ = extract_datetime(msg.data['utterance'], lang=self.lang)
        from_time = time.mktime(prev_midnight(date).timetuple())
        to_time = time.mktime(next_midnight(date).timetuple())
        if 'reminders' in self.settings:
            self.settings['reminders'] = [
                    r for r in self.settings['reminders']
                    if r[1] < from_time or r[1] > to_time]

    @intent_file_handler('GetRemindersForDay.intent')
    def get_reminders_for_day(self, msg=None):
        if 'date' in msg.data:
            date, _ = extract_datetime(msg.data['date'], lang=self.lang)
        else:
            date, _ = extract_datetime(msg.data['utterance'], lang=self.lang)
        from_time = time.mktime(prev_midnight(date).timetuple())
        to_time = time.mktime(next_midnight(date).timetuple())
        LOG.info(self.settings.get('reminders'))
        if 'reminders' in self.settings:
            reminders = [r for r in self.settings['reminders']
                         if from_time <= r[1] < to_time]
            if len(reminders) > 0:
                for r in reminders:
                    reminder_time = datetime.utcfromtimestamp(r[1])
                    self.speak(r[0] + ' at ' + nice_time(reminder_time))
                return
        self.speak('There are no reminders')

    @intent_file_handler('CancelActiveReminder.intent')
    def cancel_active(self, message):
        remove_list = []
        for c in self.cancellable:
            LOG.info(c)
            if self.remove_by_name(c):
                self.speak('Okay, reminder removed')
                remove_list.append(c)
        for c in remove_list:
            self.cancellable.remove(c)

    @intent_file_handler('SnoozeReminder.intent')
    def snooze_active(self, message):
        remove_list = []
        for c in self.cancellable:
            LOG.info(c)
            if self.reschedule_by_name(c,
                                       local_epoch() + 15 * MINUTES):
                self.speak_dialog('RemindingInFifteen')
                remove_list.append(c)
        for c in remove_list:
            self.cancellable.remove(c)

def create_skill():
    return ReminderSkill()
