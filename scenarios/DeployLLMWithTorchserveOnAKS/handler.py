from ts.torch_handler.base_handler import BaseHandler
import torch

class SimpleHandler(BaseHandler):
    def preprocess(self, data):
        return torch.tensor(data[0]['body'])

    def inference(self, input_data):
        return self.model(input_data).detach().numpy()

    def postprocess(self, inference_output):
        return inference_output.tolist()