Installing Cygwin:
- Get setup.exe from http://www.cygwin.com/install.html
- Install git, vim, and openssh from the cygwin setup

To get SSHD running on Cygwin:
- right-click the Cygwin Terminl and run Cygwin as Administrator
- run ssh-host-config
- say yes to everything except use priviledged seperation.
- select a password for the cyg_server account.
- use editrights -l -u cyg_server to view the rights for the cyg_server user
  this user should have the following rights: SeAssignPrimaryTokenPrivilege,
  SeCreateTokenPrivilege, SeTcbPrivilege, and SeServiceLogonRight.
  If the cyg_server user doesn't have one of the rights, add then using
  editrights -a SeAssignPrimaryTokenPrivilege -u cyg_server
  http://www.kgx.net.nz/2010/03/cygwin-sshd-and-windows-7/
- after ssh-host-config is completed run cygrunsrv -S sshd to start
  the sshd service

PyDAQmx:
- PyDAQmx needs to be installed for all python scripts that access
  National Instruments DAQmx cards.
- Download PyDAQmx and extract the tar.gz file.
- navigate to the directory and in the Windows cmd prompt and type:
  python setup.py install.  Once the script is completed PyDAQmx is installed.
  Type exit() to exit python.

Git Configuration:
- git does not need to be configured to begin using git, but it may be nice to
  perform this configuration.
- type git config --global user.name '<your fullname>', to configure the username
- type git config --global user.email you@email.com, to set your user email
- type git config --global color.ui true, this will show a colored interface while
  using git.  It is especially nice when using the common git-status
