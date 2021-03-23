Feature: mycroft-reminder

  Background:
    Given no reminders are set

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


  Scenario Outline: Reminder without time
    Given an english speaking user
     When the user says "remind me to be awesome"
     Then "mycroft-reminder" should reply with dialog from "ParticularTime.dialog"
     And the user says "<reminder tomorrow>"
     And "mycroft-reminder" should reply with dialog from "SavingReminderTomorrow.dialog"

  Examples:
    | reminder tomorrow |
    | tomorrow at 12 |
    | yes, tomorrow at 9am |

  Scenario Outline: Reminder without time, Negative
    Given an english speaking user
     When the user says "remind me to be awesome"
     Then "mycroft-reminder" should reply with dialog from "ParticularTime.dialog"
     And the user says "<no thanks>"
     And "mycroft-reminder" should reply with dialog from "Ok.dialog"

  Examples:
    | no thanks |
    | no thanks |
    | not really |

  Scenario: Clear all reminders
    Given an english speaking user
    And a reminder called be follow the dolphins is set for tomorrow at noon
     When the user says "clear all reminders"
     Then "mycroft-reminder" should reply with dialog from "ClearAll.dialog"
     And the user says "Yes please"
     Then "mycroft-reminder" should reply with dialog from "ClearedAll.dialog"

  Scenario: Query next reminder
    Given an english speaking user
    And a reminder called be awesome is set for tomorrow at 12
    When the user says "what is my next reminder"
    Then mycroft reply should contain "be awesome"
