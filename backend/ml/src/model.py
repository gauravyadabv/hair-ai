"""
U-Net Segmentation Architecture for Scalp & Hair Pixel Segmentation
Module E: Own AI Model Engine
"""
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    nn = object

if TORCH_AVAILABLE:
    class DoubleConv(nn.Module):
        """(Convolution => [BN] => ReLU) * 2"""
        def __init__(self, in_channels: int, out_channels: int):
            super().__init__()
            self.double_conv = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(out_channels),
                nn.ReLU(inplace=True)
            )

        def forward(self, x):
            return self.double_conv(x)


    class UNet(nn.Module):
        """
        Lightweight 4-level U-Net for binary/multi-class hair vs scalp segmentation.
        Inputs: (B, 3, H, W) normalized scalp photographs.
        Outputs: (B, 2, H, W) logits [background/scalp, hair].
        """
        def __init__(self, in_channels: int = 3, num_classes: int = 2):
            super().__init__()
            self.in_channels = in_channels
            self.num_classes = num_classes

            # Encoder
            self.inc = DoubleConv(in_channels, 32)
            self.down1 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(32, 64))
            self.down2 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(64, 128))
            self.down3 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(128, 256))
            self.down4 = nn.Sequential(nn.MaxPool2d(2), DoubleConv(256, 512))

            # Decoder with skip connections
            self.up1 = nn.ConvTranspose2d(512, 256, kernel_size=2, stride=2)
            self.conv1 = DoubleConv(512, 256)

            self.up2 = nn.ConvTranspose2d(256, 128, kernel_size=2, stride=2)
            self.conv2 = DoubleConv(256, 128)

            self.up3 = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)
            self.conv3 = DoubleConv(128, 64)

            self.up4 = nn.ConvTranspose2d(64, 32, kernel_size=2, stride=2)
            self.conv4 = DoubleConv(64, 32)

            self.outc = nn.Conv2d(32, num_classes, kernel_size=1)

        def forward(self, x):
            x1 = self.inc(x)
            x2 = self.down1(x1)
            x3 = self.down2(x2)
            x4 = self.down3(x3)
            x5 = self.down4(x4)

            x = self.up1(x5)
            x = torch.cat([x, x4], dim=1)
            x = self.conv1(x)

            x = self.up2(x)
            x = torch.cat([x, x3], dim=1)
            x = self.conv2(x)

            x = self.up3(x)
            x = torch.cat([x, x2], dim=1)
            x = self.conv3(x)

            x = self.up4(x)
            x = torch.cat([x, x1], dim=1)
            x = self.conv4(x)

            logits = self.outc(x)
            return logits

else:
    class UNet:
        """Stub when PyTorch is not yet installed."""
        def __init__(self, in_channels: int = 3, num_classes: int = 2):
            pass

