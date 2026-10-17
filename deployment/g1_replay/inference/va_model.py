"""Small VA v4/v4.1 inference network; no dataset or simulator dependency."""

from __future__ import annotations

import torch
from torch import nn


def _mlp(a: int, b: int, c: int) -> nn.Sequential:
    return nn.Sequential(nn.Linear(a, b), nn.GELU(), nn.Linear(b, c))


class _CrossAttention(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.qnorm = nn.LayerNorm(256)
        self.vnorm = nn.LayerNorm(256)
        self.attn = nn.MultiheadAttention(256, 4, batch_first=True)
        self.norm = nn.LayerNorm(256)
        self.ff = _mlp(256, 512, 256)

    def forward(self, query, visual):
        value = self.vnorm(visual)
        query = query + self.attn(self.qnorm(query), value, value, need_weights=False)[0]
        return (query + self.ff(self.norm(query)))[:, 0]


class VAPolicy(nn.Module):
    def __init__(self, *, v41: bool = True) -> None:
        super().__init__()
        layers = []
        for a, b in zip([3, 32, 64, 128], [32, 64, 128, 256]):
            layers += [nn.Conv2d(a, b, 3, 2, 1), nn.GroupNorm(8, b), nn.GELU()]
        self.visual = nn.Sequential(*layers)
        self.position = nn.Parameter(torch.randn(1, 64, 256) * 0.02)
        self.body_query = nn.Sequential(_mlp(68, 256, 256), nn.LayerNorm(256), nn.GELU())
        self.grasp_query = nn.Sequential(_mlp(68, 256, 256), nn.LayerNorm(256), nn.GELU())
        self.body_cross = _CrossAttention()
        self.grasp_cross = _CrossAttention()
        self.hand_state = nn.Sequential(_mlp(28, 128, 128), nn.GELU())
        self.body_feature = nn.Sequential(_mlp(256, 512, 512), nn.GELU())
        self.body_head = _mlp(512, 512, 640)
        self.phase_feature = nn.Sequential(nn.Linear(256, 64), nn.GELU())
        self.phase_head = nn.Linear(64, 3)
        self.progress_head = nn.Linear(64, 1)
        self.hand_head = nn.Sequential(nn.Linear(448, 512), nn.GELU(), _mlp(512, 512, 700))
        self.grasp_ready_head = nn.Linear(256, 1) if v41 else None
        self.register_buffer("body_mean", torch.zeros(68))
        self.register_buffer("body_std", torch.ones(68))
        self.register_buffer("hand_mean", torch.zeros(28))
        self.register_buffer("hand_std", torch.ones(28))

    def forward(self, rgb, body, hand):
        batch = len(rgb)
        if rgb.shape[1:] != (3, 128, 128) or body.shape != (batch, 68) or hand.shape != (batch, 28):
            raise ValueError("expected RGB [B,3,128,128], body [B,68], hand [B,28]")
        visual = self.visual(rgb).flatten(2).transpose(1, 2) + self.position
        body = (body - self.body_mean) / self.body_std
        hand = (hand - self.hand_mean) / self.hand_std
        body_context = self.body_cross(self.body_query(body)[:, None], visual)
        grasp_context = self.grasp_cross(self.grasp_query(body)[:, None], visual)
        phase = self.phase_feature(grasp_context)
        result = {
            "body_tokens": self.body_head(self.body_feature(body_context)).reshape(-1, 10, 64),
            "hand_ref": self.hand_head(torch.cat([grasp_context, phase, self.hand_state(hand)], -1)).reshape(-1, 50, 14),
            "phase_logits": self.phase_head(phase),
            "closure_progress": self.progress_head(phase).sigmoid()[:, 0],
        }
        if self.grasp_ready_head is not None:
            result["grasp_ready_logit"] = self.grasp_ready_head(grasp_context)
        return result

