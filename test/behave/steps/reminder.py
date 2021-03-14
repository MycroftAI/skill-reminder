import time

from behave import given

from mycroft.audio import wait_while_speaking
from test.integrationtests.voight_kampff import (
        emit_utterance,
        wait_for_dialog)


@given('a reminder called {name} is set for {time}')
def given_reminder(context, name, time):
    emit_utterance(context.bus, 'remind me to {} at {}'.format(name, time))
    wait_for_dialog(context.bus, ['SavingReminder', 'SavingReminderTomorrow',
                                  'SavingReminderDate'])
    context.bus.clear_messages()


@given('no reminders are set')
def given_no_reminders(context):
    followups = ['ClearAll']

    emit_utterance(context.bus, 'clear all reminders')
    for i in range(10):
        for message in context.bus.get_messages('speak'):
            if message.data.get('meta', {}).get('dialog') in followups:
                time.sleep(3)
                wait_while_speaking()
                emit_utterance(context.bus, 'yes')
                wait_for_dialog(context.bus, ['ClearedAll'])
                context.bus.clear_messages()
                return
        time.sleep(1)
