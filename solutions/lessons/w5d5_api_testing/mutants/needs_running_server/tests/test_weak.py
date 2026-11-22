import httpx


def test_predict_on_running_server():
    r = httpx.post("http://127.0.0.1:8000/predict", json={"burn_in": [0.0, 1.0], "values": [0.5]})
    assert r.status_code == 200


def test_bad_request_on_running_server():
    r = httpx.post("http://127.0.0.1:8000/predict", json={"values": []})
    assert r.status_code == 422
