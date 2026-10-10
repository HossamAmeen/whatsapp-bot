.PHONY: restart logs

restart:
	sudo systemctl restart whatsapp-bot

logs:
	tail -n 100 -f logs/webhook.log
