DOCKER:

1 - Edit image version in compose.yaml

2 - Build Image
docker compose up --build # to build and run
or
docker compose build # only build

3 - Push Image do Hub
docker image push mcjgalvao/urachatmonitor-server:{version}

KUBERNETES:

1 - Enable kubernetes support in docker configuration



