
import os
FAST_EVAL = os.environ.get("FAST_EVAL", "0") == "1"
if FAST_EVAL:
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import matplotlib.pyplot as plt

# Define the autoencoder model
class Autoencoder(nn.Module):
    def __init__(self):
        super(Autoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(28 * 28, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 12),
            nn.ReLU(),
            nn.Linear(12, 3)  # Bottleneck layer
        )
        self.decoder = nn.Sequential(
            nn.Linear(3, 12),
            nn.ReLU(),
            nn.Linear(12, 64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, 28 * 28),
            nn.Sigmoid()
        )

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x

# Load the MNIST dataset
transform = transforms.Compose([transforms.ToTensor(), transforms.Normalize((0.5,), (0.5,))])
train_dataset = datasets.MNIST(root='./data', train=True, download=True, transform=transform)
train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=64, shuffle=True)

# Initialize the autoencoder and optimizer
autoencoder = Autoencoder()
optimizer = optim.Adam(autoencoder.parameters(), lr=0.001)

# Training loop
num_epochs = 5
for epoch in range(num_epochs):
    for data in train_loader:
        images, _ = data
        images = images.view(-1, 28 * 28)

        optimizer.zero_grad()
        outputs = autoencoder(images)
        loss = nn.MSELoss()(outputs, images)
        loss.backward()
        optimizer.step()

    print(f'Epoch [{epoch+1}/{num_epochs}], Loss: {loss.item():.4f}')

# Test the autoencoder
test_dataset = datasets.MNIST(root='./data', train=False, download=True, transform=transform)
test_loader = torch.utils.data.Dataloader(test_dataset, batch_size=64, shuffle=False)

with torch.no_grad():
    for data in test_loader:
        images, _ = data
        images = images.view(-1, 28 * 28)
        outputs = autoencoder(images)
        reconstruction_loss = nn.MSELoss()(outputs, images)
        assert reconstruction_loss < 0.02, f"Reconstruction loss {reconstruction_loss:.6f} is not below 0.02"

        # Visualize the reconstructed images
        fig, axs = plt.subplots(2, 10, figsize=(10, 2))
        for i in range(10):
            axs[0, i].imshow(images[i].view(28, 28).numpy(), cmap='gray')
            axs[0, i].axis('off')
            axs[1, i].imshow(outputs[i].view(28, 28).detach().numpy(), cmap='gray')
            axs[1, i].axis('off')
        print('[FAST_EVAL] plt.show() skipped')
        break