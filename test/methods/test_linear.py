

import pytest
import torch
import torch.nn as nn
from solo.methods.linear import LinearModel
from torchvision.models import resnet18

from .utils import (
    gen_base_cfg,
    gen_classification_batch,
    gen_trainer,
    prepare_classification_dummy_dataloaders,
)


def test_linear():
    cfg = gen_base_cfg("none", batch_size=2, num_classes=100)

    backbone = resnet18()
    backbone.fc = nn.Identity()

    model = LinearModel(backbone, cfg=cfg)
    trainer = gen_trainer(cfg)

    # test arguments
    model.add_and_assert_specific_cfg(cfg)

    batch, _ = gen_classification_batch(
        cfg.optimizer.batch_size, cfg.data.num_classes, "imagenet100"
    )
    out = model(batch[0])

    assert (
        "logits" in out
        and isinstance(out["logits"], torch.Tensor)
        and out["logits"].size() == (cfg.optimizer.batch_size, cfg.data.num_classes)
    )
    assert (
        "feats" in out
        and isinstance(out["feats"], torch.Tensor)
        and out["feats"].size() == (cfg.optimizer.batch_size, model.backbone.inplanes)
    )

    trainer = gen_trainer(cfg)
    train_dl, val_dl = prepare_classification_dummy_dataloaders(
        "imagenet100",
        num_classes=cfg.data.num_classes,
    )
    trainer.fit(model, train_dl, val_dl)

    # test optimizers/scheduler
    model.optimizer = "random"
    model.scheduler = "none"
    with pytest.raises(AssertionError):
        model.configure_optimizers()

    model.optimizer = "sgd"
    model.scheduler = "none"
    optimizer = model.configure_optimizers()
    assert isinstance(optimizer, torch.optim.Optimizer)

    model.scheduler = "reduce"
    scheduler = model.configure_optimizers()[1][0]
    assert isinstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau)

    model.scheduler = "step"
    scheduler = model.configure_optimizers()[1][0]
    assert isinstance(scheduler, torch.optim.lr_scheduler.MultiStepLR)

    model.scheduler = "exponential"
    scheduler = model.configure_optimizers()[1][0]
    assert isinstance(scheduler, torch.optim.lr_scheduler.ExponentialLR)

    model.scheduler = "random"
    with pytest.raises(ValueError):
        model.configure_optimizers()

    model.optimizer = "adam"
    model.scheduler = "none"
    model.extra_optimizer_args = {}
    optimizer = model.configure_optimizers()
    assert isinstance(optimizer, torch.optim.Optimizer)
