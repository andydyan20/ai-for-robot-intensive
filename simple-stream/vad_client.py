import tritonclient.grpc as grpcclient
import numpy as np

client = grpcclient.InferenceServerClient(url="localhost:8002")

class VadClient:
    def __init__(self, url="localhost:8002"):
        self.client = grpcclient.InferenceServerClient(url=url)
        self.started = False

    def infer(self, chunk: np.ndarray):
        inputs = []

        inputs.append(self._add_input("INPUT", chunk, "INT16"))
        inputs.append(self._add_input("SESSION", np.array([["session-1"]], dtype=object), "BYTES"))
        inputs.append(self._add_input("THRESHOLD", np.array([[0.5]], dtype=np.float16), "FP16"))
        inputs.append(self._add_input("RATE", np.array([[16000]], dtype=np.int16), "INT16"))
        inputs.append(self._add_input("VOLUME", np.array([[0.0]], dtype=np.float16), "FP16"))
        inputs.append(self._add_input("START_SECS", np.array([[0.3]], dtype=np.float16), "FP16"))
        inputs.append(self._add_input("STOP_SECS", np.array([[0.5]], dtype=np.float16), "FP16"))

        result = self.client.infer(
            model_name="vad",
            inputs=inputs,
            sequence_id=1,
            sequence_start=not self.started,
            sequence_end=False,
        )
        if result is None:
            return {"error": "No response from Triton"}

        self.started = True

        return {
            "signal": result.as_numpy("SIGNAL"),
            "output": result.as_numpy("OUTPUT"),
        }
    
    def _add_input(self, name, value, datatype) -> grpcclient.InferInput:
        inp = grpcclient.InferInput(
            name,
            list(value.shape),
            datatype,
        )
        inp.set_data_from_numpy(value)
        return inp


vad_client = VadClient()

