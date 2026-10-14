# Corporate laptop: shortcuts for myproxy, the local Kerberos proxy on 127.0.0.1:9080.
# Sourced from .zshrc. Setup and why: proxy-hell/ (encrypted).
#
# The LaunchAgents are labelled com.<mac user>.*; $USER fills that in, so the account
# name stays out of this public repo.

# Edge through myproxy. Quit Edge with Cmd+Q first -- launched from the Dock it skips the flag.
alias edge='open -na "Microsoft Edge" --args --proxy-server="http://127.0.0.1:9080" --proxy-bypass-list="*.db.com;localhost;127.0.0.1"'

# Renew the Kerberos ticket now and restart myproxy, instead of waiting for the 15-minute agent.
alias krenew="launchctl kickstart gui/\$(id -u)/com.$USER.krb-renew && launchctl kickstart -k gui/\$(id -u)/com.$USER.myproxy"
