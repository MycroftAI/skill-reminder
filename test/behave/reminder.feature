Feature: mycroft-reminder

  Scenario: Reminder in 2 days
    Given an english speaking user
     When the user says "remind me to be awesome in 2 days"
     Then "mycroft-reminder" should reply with dialog from "SavingReminderDate.dialog"

  Scenario: Reminder during night
    Given an english speaking user
     When the user says "remind me to sleep at 1 a.m."
     Then "mycroft-reminder" should reply with dialog from "ItIsNight.dialog"
     And the user says "yes"
     And "mycroft-reminder" should reply with dialog from "SavingReminderTomorrow.dialog"
