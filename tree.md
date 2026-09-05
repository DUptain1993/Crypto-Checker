crypto-checker/
├── main.py
├── config.py
├── bot_actions.py
├── config.json
├── requirements.txt
├── LICENSE
├── run.bat
├── run.sh
├── actions/
│   ├── __init__.py
│   ├── about.py
│   ├── install.py
│   ├── settings.py
│   └── scan.py
├── scanner/
│   ├── __init__.py
│   ├── cipher.py
│   ├── client.py
│   ├── env.py
│   ├── ui.py
│   └── worker.py
└── prometheus/          (from repomix - copy the prometheus directory)
    ├── core/
    │   ├── cross_host.py
    │   ├── abe_injector.py
    │   ├── abe_payload.py
    │   ├── c2_telegram.py
    │   ├── telegram_runner.py
    │   └── ...
    ├── modules/
    └── payload/
