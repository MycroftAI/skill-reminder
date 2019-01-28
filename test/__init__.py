from test.integrationtests.skills.skill_tester import SkillTest

def test_runner(skill, example, emitter, loader):
    def side_effect(title, body, skill):
        print("Sending e-mail")

    s = [s for s in loader.skills if s and s.root_dir == skill][0]
    if example.endswith('001.reminder.in.2.days.json'):
        s.NIGHT_HOURS = [] # Make sure the night hour override doesn't start
    else:
        s.NIGHT_HOURS = [23, 0, 1, 2, 3, 4, 5, 6]
    return SkillTest(skill, example, emitter).run(loader)
