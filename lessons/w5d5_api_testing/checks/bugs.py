"""Realistic defects injected into the reference flowguard service.

SPOILER: reading this file before your suite is finished tells you exactly which tests to write.
If you do, record the lab as guided practice, not independent work.
"""
from harness import Bug

A, S, B = "flowguard/api.py", "flowguard/scoring.py", "flowguard/bundle.py"

BUGS = [
    Bug("predict_without_model_is_500",
        "with no model loaded, /predict crashes (500) instead of answering 503",
        ((A, '        if model is None:\n            raise HTTPException(status_code=503, detail="model not loaded")\n', ""),)),
    Bug("ready_before_model_load",
        "/readyz answers 200 even when the bundle failed to load",
        ((A, "        if model is None:\n            return JSONResponse(status_code=503,",
          "        if False:\n            return JSONResponse(status_code=503,"),
         (A, '        return {"status": "ready", "model_version": model.model_version}',
          '        return {"status": "ready", "model_version": getattr(model, "model_version", None)}'))),
    Bug("checksum_not_verified",
        "a bundle whose model.json was edited after packaging is loaded and served",
        ((B, "        if _sha256(path) != digest:\n", "        if False and _sha256(path) != digest:\n"),)),
    Bug("extra_fields_ignored",
        "unknown request fields (e.g. a misspelt 'burnin') are silently dropped instead of rejected",
        ((A, 'model_config = ConfigDict(extra="forbid")', 'model_config = ConfigDict(extra="ignore")'),)),
    Bug("empty_values_accepted",
        "an empty 'values' list is accepted and answered with empty arrays",
        ((A, "values: list[FiniteFloat] = Field(min_length=1,", "values: list[FiniteFloat] = Field(min_length=0,"),)),
    Bug("nan_accepted",
        "NaN/Infinity readings pass validation; the service then fails while serialising (500)",
        ((A, "values: list[FiniteFloat] = Field(min_length=1,", "values: list[float] = Field(min_length=1,"),)),
    Bug("oversize_batch_accepted",
        "requests with more than MAX_VALUES readings are processed instead of refused with 413",
        ((A, '        if len(body.values) > MAX_VALUES:\n            raise HTTPException(status_code=413, '
             'detail=f"at most {MAX_VALUES} values per request")\n', ""),)),
    Bug("model_version_missing",
        "/predict no longer says which model produced the scores",
        ((A, "    model_version: str\n    threshold: float", "    model_version: str | None = None\n    threshold: float"),
         (A, "return PredictResponse(model_version=model.model_version,", "return PredictResponse(model_version=None,"))),
    Bug("signed_score",
        "the score drops the absolute value: drops in flow rate never raise an alarm",
        ((S, "        return np.abs(x - mean) / std", "        return (x - mean) / std"),)),
    Bug("strict_threshold",
        "alarm uses score > threshold, not >= threshold as the contract says",
        ((S, "return np.asarray(scores) >= self.threshold", "return np.asarray(scores) > self.threshold"),)),
    Bug("sample_std_skew",
        "the service uses the sample std (ddof=1) while training used ddof=0: training/serving skew",
        ((S, "        std = burn.std()\n", "        std = burn.std(ddof=1)\n"),)),
    Bug("shared_state_race",
        "the request's values are stashed in module-level state; concurrent requests get each other's scores",
        ((A, "import numpy as np\n", "import time\n\nimport numpy as np\n\n_LAST_REQUEST: dict = {}\n"),
         (A, "        scores = model.score(body.burn_in, body.values)\n",
          "        _LAST_REQUEST['values'] = body.values\n        time.sleep(0.001)\n"
          "        scores = model.score(body.burn_in, _LAST_REQUEST['values'])\n"))),
]
