how to pack:
pyinstaller --name=ATC_Logger --windowed --onefile --clean --noconfirm --hidden-import=PyQt5.QtCore --hidden-import=PyQt5.QtGui --hidden-import=PyQt5.QtWidgets --hidden-import=pexpect --hidden-import=ptyprocess UI/atc.py


pyinstaller --onefile --windowed --name="ATC" \
  --hidden-import=commands.check_diags_command \
  --hidden-import=commands.collectlog_command \
  --hidden-import=commands.nanocom_command \
  --hidden-import=commands.collect_command \
  --hidden-import=routes.check_diags \
  --hidden-import=routes.collectlog \
  --hidden-import=routes.sysconfig_read \
  --hidden-import=pexpect \
--hidden-import=glob \
--hidden-import=json \
  --hidden-import=pty \
  --hidden-import=fcntl \
  --add-data="commands:commands" \
  --add-data="routes:routes" \
  --add-data="utils:utils" \
  atc.py