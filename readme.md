# Shoujin Slack Notifier

## what is this

AtCoderやCodeforcesでの精進の記録をslackにpostします

## how to use

1.  [Incoming WebHooks](https://slack.com/apps/A0F7XDUAZ-incoming-webhooks) を導入して WebHook URL を得る
2.  `$ python3 shoujin.py` すると `~/.config/shoujin-slack-notifier/config.json` が作られるので適当に書き換え
    -   `users` は名前とAtCoderやCodeforcesのID
    -   `webhook-url` はslackのそれ
3.  再び `$ python3 shoujin.py`
4.  cronなどに `$ python3 shoujin.py` を設定
