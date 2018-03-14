# AtCoder Shoujin Slack Notifier

## what is this

AtCoderでの精進の記録をslackにpostします

## how to use

1.  [Incoming WebHooks](https://slack.com/apps/A0F7XDUAZ-incoming-webhooks) を導入して WebHook URL を得る
2.  `$ python3 shoujin.py --no-post` すると `~/.config/shoujin-slack-notifier/config.json` が作られるのでに書き換え
    -   `users` はAtCoderのID
    -   `webhook-url` はslackのそれ
3.  再び `$ python3 shoujin.py --no-post`
4.  cronなどに `$ python3 shoujin.py` を設定
