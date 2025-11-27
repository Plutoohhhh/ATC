from utils.command_runner import CommandRunner
from routes import scout_validate


class ScoutValidateCommand(CommandRunner):
    def execute(self):
        scouter = scout_validate.ScoutValidate()
        scouter.set_logger(self.logger)

        return scouter.main()