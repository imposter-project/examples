# WireMock examples

See the [WireMock plugin documentation](https://docs.imposter.sh/wiremock_plugin/) for how to enable WireMock support.

## Example

Let's assume your configuration is in a folder named `wiremock-simple`.

CLI example:

    imposter up ./wiremock-simple --engine-type docker-all

Docker example:

    docker run -ti -p 8080:8080 \
        -v $PWD/wiremock-simple:/opt/imposter/config \
        outofcoffee/imposter-all

Standalone Java example:

    java -jar distro/all/build/libs/imposter-all.jar \
        --configDir ./wiremock-simple

This starts a mock server using the WireMock plugin. Responses are served based on the mappings files inside the `wiremock-simple/mappings` folder and the templated response files in the `wiremock-simple/__files` folder.

Using the example above, Imposter will parse the WireMock mappings files and create an HTTP mock on [http://localhost:8080/](http://localhost:8080/).

### Testing the mock

```bash
curl http://localhost:8080/example1 -H 'Accept: application/json'

{ "id": 2, "name": "Dog" }
```
