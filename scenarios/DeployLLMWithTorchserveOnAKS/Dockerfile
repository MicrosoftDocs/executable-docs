FROM pytorch/torchserve:latest

# Copy the model archive into the model store
COPY llm_model.mar /home/model-server/model-store/

# Expose TorchServe ports
EXPOSE 8080 8081

# Start TorchServe
CMD ["torchserve", "--start", "--model-store", "/home/model-server/model-store", "--models", "llm_model.mar"]