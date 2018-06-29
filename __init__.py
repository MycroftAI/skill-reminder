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
from datetime import datetime, timedelta
from parsedatetime import Calendar
from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.parse import extract_datetime
from mycroft.util.format import nice_time
from mycroft.util.log import LOG

class ReminderSkill(MycroftSkill):
    def __init__(self):
        super(ReminderSkill, self).__init__()
        self.notes = {}
        self.primed = False

    def initialize(self):
        self.add_event('speak', self.prime)
        self.add_event('mycroft.skill.handler.complete', self.notify)
        self.add_event('mycroft.skill.handler.start', self.reset)

        self.schedule_repeating_event(self.__check_reminder, datetime.now(),
                                      120, name='reminder')

    def add_notification(self, identifier, note, expiry):
        self.notes[identifier] = (note, expiry)

    def prime(self, message):
        LOG.info('PRIMING NOTIFICATION')
        self.primed = True

    def reset(self, message):
        time.sleep(10)
        LOG.info('RESETTING NOTIFICATION')
        self.primed = False

    def notify(self, message):
        LOG.info('notify: {}'.format(self.primed))
        handled_reminders = []
        now = time.time()
        if self.primed:
            for r in self.settings.get('reminders', []):
                print('Checking {}'.format(r))
                if now > r[1] - 600 and now < r[1]:
                    handled_reminders.append(r)
                    self.speak_dialog('by.the.way', data={'reminder': r[0]})
            self.remove_handled(handled_reminders)
            self.primed = False

    def __check_reminder(self, message):
        self.log.info('Checking reminders')
        now = time.time()
        handled_reminders = []
        for r in self.settings.get('reminders', []):
            if now > r[1]:
                self.speak(r[0])
                handled_reminders.append(r)
            if now > r[1] - 600:
                self.add_notification(r[0], r[0], r[1])
        self.remove_handled(handled_reminders)

    def remove_handled(self, handled_reminders):
        for r in handled_reminders:
            self.settings['reminders'].remove(r)

    @intent_file_handler('ReminderAt.intent')
    def add_new_reminder(self, msg=None):
        print(msg.data)
        reminder = msg.data.get('reminder', '')
        reminder.replace(' my ', ' your ')
        reminder_time = extract_datetime(msg.data['utterance'],
                                         datetime.now())[0] # start time
        LOG.info(reminder_time)
        # convert to UTC
        self.speak_dialog('SavingReminder',
                          {'timedate': nice_time(reminder_time)})

        self.__save_reminder_local(reminder, reminder_time)

    @intent_file_handler('ReminderIn.intent')
    def add__reminder_in(self, msg=None):
        LOG.info('REMINDER IN!')
        reminder = msg.data.get('reminder', None)
        print(reminder)
        reminder = reminder.replace(' my ', ' your ')
        print(reminder)
        reminder_time = Calendar().parseDT(msg.data['timedate'])[0]
        LOG.info(reminder_time)
        # convert to UTC
        self.speak_dialog('SavingReminder',
                          {'timedate': nice_time(reminder_time)})
        self.__save_reminder_local(reminder, reminder_time)

    def __save_reminder_local(self, reminder, reminder_time):
        since_epoch = time.mktime(reminder_time.timetuple())
        if 'reminders' in self.settings:
            self.settings['reminders'].append((reminder, since_epoch))
        else:
            self.settings['reminders'] = [(reminder, since_epoch)]

    @intent_file_handler('DeleteReminderForDay.intent')
    def remove_reminders_for_day(self, msg=None):
        if date in msg.data:
            date = extract_datetime(msg.data['date'])
        else:
            date = extract_datetime(msg.data['utterance'])
        


def create_skill():
    return ReminderSkill()
