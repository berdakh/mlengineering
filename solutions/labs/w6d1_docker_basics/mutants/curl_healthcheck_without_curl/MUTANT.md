# curl_healthcheck_without_curl
Plausible mistake: the HEALTHCHECK from a tutorial, `curl -f http://localhost:8000/readyz`, in an image that has no curl. The check can never succeed and the container is reported unhealthy, even though the API works. Expected to fail: test_healthcheck_asks_the_service_with_a_tool_the_image_has.
