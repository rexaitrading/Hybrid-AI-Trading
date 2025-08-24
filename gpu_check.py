import torch

print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("Device:", torch.cuda.get_device_name(0))
    x = torch.rand(2000, 2000, device="cuda")
    y = x @ x
    print("OK:", y.shape, y.device)