[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

# Whatsapper integration

The integration to use [Whatsapper](https://github.com/baldarn/whatsapper) in home assistant!

## Getting started

Install Whatsapper add on.

You can find that in [alexbelgium](https://github.com/alexbelgium/hassio-addons)

### Installation
Whatsapper is now part ot the Default HACS repositories list.
Just add it from the Integrations list.

### Configuration
To use Whatsapper notifications edit the `configuration.yaml` file.

```yaml
notify:
  - platform: whatsapper
    name: some name that you want
    chat_id: 123123123@g.us # WhatsApp chat id (see below)
```

#### Get chat id

To get all you chat ids, go on the web browser and call (using your home assistant ip):

```url
http://192.168.1.123:4000/chats
```

Search and find the chat where you want to send messages and get it's id

### Whatsapper host_port configuration

If your whatsapper instance is somewhere else, you can specify that:

```yaml
notify:
  - platform: whatsapper
    name: some name that you want
    host_port: 192.168.1.123:4000 # host:port of the whatsapper instance
    chat_id: 123123123@g.us # WhatsApp chat id
```
