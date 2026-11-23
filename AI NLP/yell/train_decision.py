"""Ajuste supervisado de DistilBERT. El modo de verificación usa solo dos lotes."""
import json
import random
import time
import tempfile
from pathlib import Path
from statistics import median

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

from .decision import LABELS, WEIGHTS, DecisionModel, decide
from .decision_data import DATA, read_data
from .transfer import BASE


def evaluate(model, rows):
    good = wrong_person = false_order = 0
    times = []
    for row in rows:
        start = time.perf_counter()
        decision, _ = decide(model, row["text"], row["aliases"], row["roster"], row["here"])
        times.append((time.perf_counter()-start)*1000)
        key = (decision.get("accion","charla"), decision.get("sujeto",{}).get("id"),
               decision.get("lugar"), decision.get("objetivo",{}).get("id"))
        good += key == (row["label"],row["subject"],row["location"],row["target"])
        false_order += key[0] != "charla" and row["label"] == "charla"
        wrong_person += key[0] != "charla" and row["subject"] is not None and key[1] != row["subject"]
    return dict(n=len(rows),exactos=good,exactitud=good/len(rows),charlas_ejecutadas=false_order,
                destinatarios_erroneos=wrong_person,mediana_ms=median(times))


def train(output=WEIGHTS, epochs=12, batch_size=16, patience=3, smoke=False):
    torch.manual_seed(421)
    random.seed(421)
    if not torch.cuda.is_available() and not smoke:
        raise RuntimeError("Selecciona el kernel CUDA del proyecto.")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    splits = read_data()
    if smoke:
        splits = {k:random.sample(v,min(len(v),2*batch_size)) for k,v in splits.items()}
        epochs = 1
    tok = AutoTokenizer.from_pretrained(BASE,local_files_only=True)
    net = AutoModelForSequenceClassification.from_pretrained(BASE,num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)),label2id={k:i for i,k in enumerate(LABELS)},
        local_files_only=True,seq_classif_dropout=.20).to(device)
    net.base_model.requires_grad_(False)
    for block in net.base_model.transformer.layer[-2:]:
        block.requires_grad_(True)
    def collate(rows):
        inputs = tok([r["encoded"] for r in rows],padding=True,truncation=True,max_length=80,return_tensors="pt")
        return inputs.to(device), torch.tensor([LABELS.index(r["label"]) for r in rows],device=device)
    batches = {k:torch.utils.data.DataLoader(v,batch_size=batch_size,shuffle=k=="train",collate_fn=collate)
               for k,v in splits.items()}
    head = [p for n,p in net.named_parameters() if p.requires_grad and not n.startswith("distilbert.")]
    opt = torch.optim.AdamW([{"params":[p for p in net.base_model.parameters() if p.requires_grad],"lr":3e-5},
                             {"params":head,"lr":3e-4}],weight_decay=.02)
    steps = epochs*len(batches["train"])
    sched = get_linear_schedule_with_warmup(opt,int(.08*steps),steps)
    scaler = torch.amp.GradScaler("cuda",enabled=device=="cuda")
    loss_fn = torch.nn.CrossEntropyLoss(label_smoothing=.03)
    output.mkdir(parents=True,exist_ok=True)
    published = output
    output = Path(tempfile.mkdtemp(prefix="run-",dir=published))
    history = []
    best = float("inf")
    for epoch in range(epochs):
        net.train()
        for x,y in batches["train"]:
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device,enabled=device=="cuda"):
                loss = loss_fn(net(**x).logits,y)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(net.parameters(),1)
            scale = scaler.get_scale()
            scaler.step(opt)
            scaler.update()
            if scaler.get_scale() >= scale: sched.step()
        net.eval()
        total = 0.
        with torch.inference_mode():
            for x,y in batches["val"]:
                total += loss_fn(net(**x).logits,y).item()*len(y)
        val = total/len(splits["val"])
        history.append(dict(epoch=epoch+1,val_loss=val))
        print(history[-1],flush=True)
        if val < best:
            best, best_epoch = val, epoch
            net.config.decision_threshold = .65
            net.save_pretrained(output)
            tok.save_pretrained(output)
        if epoch-best_epoch >= patience: break
    del net,opt
    model = DecisionModel(output,device)
    # Calibrate on validation only. Penalize chat that could move a unit.
    candidates = []
    for threshold in (.45,.55,.65,.75,.85):
        model.threshold = threshold
        stats = evaluate(model,splits["val"])
        candidates.append((stats["exactos"]-2*stats["charlas_ejecutadas"],threshold))
    model.threshold = max(candidates)[1]
    model.net.config.decision_threshold = model.threshold
    model.net.config.save_pretrained(output)
    report = dict(device=device,smoke=smoke,history=history,threshold=model.threshold,test=evaluate(model,splits["test"]))
    if not smoke:
        spoken = [json.loads(line) for line in (DATA/"transcripciones.jsonl").read_text(encoding="utf8").splitlines() if line]
        report["diagnostico_transcripciones"] = evaluate(model,spoken)
    (output/"evaluacion.json").write_text(json.dumps(report,indent=2),encoding="utf8")
    marker = published/(output.name+".tmp")
    marker.write_text(output.name,encoding="utf8")
    marker.replace(published/"actual.txt")
    return report

