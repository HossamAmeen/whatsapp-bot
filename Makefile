.PHONY: restart logs

restart:
	sudo systemctl restart whatsapp-bot

logs:
	sudo journalctl -u whatsapp-bot -n 100 -f
