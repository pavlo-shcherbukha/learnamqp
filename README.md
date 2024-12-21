# learnamqp  Вивчення використання amqp

## Постановка проблеми
Навчитися працювати з RabbotMQ за python

## Користні лінки

[Docker RabbitMQ](https://hub.docker.com/_/rabbitmq/)
[Rabbit tutorials](https://www.rabbitmq.com/tutorials)
[habre](https://habr.com/ru/articles/434510/)
[Getting Started with RabbitMQ and Python: A Practical Guide. Docker compose](https://dev.to/felipepaz/getting-started-with-rabbitmq-and-python-a-practical-guide-57fi)

https://github.com/pazfelipe/python-rabbitmq/tree/main


## RUN DOCKER

```bash
docker pull rabbitmq

docker run -d --hostname my-rabbit --name some-rabbit rabbitmq:3

docker run -d --hostname my-rabbit --name some-rabbit -e RABBITMQ_DEFAULT_USER=user -e RABBITMQ_DEFAULT_PASS=password rabbitmq:3-management

docker run -d --hostname my-rabbit --name some-rabbit -e RABBITMQ_DEFAULT_VHOST=my_vhost rabbitmq:3-management

docker-compose up -d
```

Got to the management console

http://localhost:15672/

guest/guest




```bash

docker-compose -f docker-compose-websender.yaml up --remove-orphans --build sender-web

docker-compose -f docker-compose-websender.yaml stop

```