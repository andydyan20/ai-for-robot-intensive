import numpy as np
import tritonclient.grpc as grpcclient

InferInput = grpcclient.InferInput
InferRequestedOutput = grpcclient.InferRequestedOutput
InferResult = grpcclient.InferResult

OUTPUT_FIELDS = ("text", "endpoint_type", "version", "rescore", "sil_dur")
OUTPUT_SCHEMA = [InferRequestedOutput(field) for field in OUTPUT_FIELDS]


def AsrInput(chunk: bytes, callid: str, domain: str, endpoint: float) -> list[InferInput]:
    speech_dat = np.frombuffer(chunk, np.int16)[None]
    dats = (
        ("speech_wav", "INT16", speech_dat),
        ("callid", "BYTES", np.array([[callid]], np.bytes_)),
        ("domain", "BYTES", np.array([[domain]], np.bytes_)),
        ("endpoint", "FP32", np.array([[endpoint]], np.float32)),
    )

    inputs = []
    for key, xtype, x in dats:
        inp = InferInput(key, x.shape, xtype)
        inp.set_data_from_numpy(x)
        inputs.append(inp)
    return inputs


def AsrOutput(result: InferResult) -> dict:
    text = _required_output(result, "text").item().decode()
    etype = _required_output(result, "endpoint_type").item()
    eos = text and etype > 0
    return dict(
        version=_required_output(result, "version").item().decode(),
        sil_dur=round(_required_output(result, "sil_dur")[0], 3),
        endpoint_type=etype,
        text=text,
        rescore=[x.decode() for x in _required_output(result, "rescore")] if eos else [],
    )


def _required_output(result: InferResult, name: str) -> np.ndarray:
    output = result.as_numpy(name)
    if output is None:
        raise ValueError(f"Missing Triton output: {name}")
    return output


class AsrTritonClient:
    def __init__(
        self,
        url: str = "localhost:8001",
        model_name: str = "asr-triton",
        sequence_id: int = 1,
        headers: dict | None = None,
    ):
        self.client = grpcclient.InferenceServerClient(url=url)
        self.model_name = model_name
        self.sequence_id = sequence_id
        self.headers = headers
        self.started = False

    def infer(
        self,
        chunk: bytes | np.ndarray,
        callid: str,
        domain: str,
        endpoint: float = 0.0,
        final: bool = False,
    ) -> dict:
        chunk_bytes = self._pcm16_bytes(chunk)
        sequence_end = final or endpoint > 0
        inputs = AsrInput(chunk_bytes, callid, domain, endpoint)

        result = self.client.infer(
            model_name=self.model_name,
            inputs=inputs,
            outputs=OUTPUT_SCHEMA,
            sequence_id=self.sequence_id,
            sequence_start=not self.started,
            sequence_end=sequence_end,
            headers=self.headers,
        )
        if result is None:
            return {"error": "No response from Triton"}

        self.started = True
        if sequence_end:
            self.started = False

        return AsrOutput(result)

    def _pcm16_bytes(self, chunk: bytes | np.ndarray) -> bytes:
        if isinstance(chunk, bytes):
            return chunk
        audio = np.asarray(chunk).reshape(-1)
        if audio.dtype == np.int16:
            return np.ascontiguousarray(audio).tobytes()
        if np.issubdtype(audio.dtype, np.floating):
            return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
        return audio.astype(np.int16, copy=False).tobytes()

asr_triton_client = AsrTritonClient()

