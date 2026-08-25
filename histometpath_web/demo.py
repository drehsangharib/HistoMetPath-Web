from __future__ import annotations
import numpy as np
import pandas as pd

EXAMPLES = {
    "Sparse tumor signal": {"seed": 7, "positive_fraction": 0.10, "pattern": "sparse"},
    "Diffuse tumor signal": {"seed": 13, "positive_fraction": 0.42, "pattern": "diffuse"},
    "Spatially heterogeneous": {"seed": 23, "positive_fraction": 0.25, "pattern": "clustered"},
    "Non-tumor example": {"seed": 31, "positive_fraction": 0.02, "pattern": "negative"},
}

def make_slide(name: str, grid_size: int = 12) -> pd.DataFrame:
    cfg = EXAMPLES[name]
    rng = np.random.default_rng(cfg["seed"])
    y, x = np.mgrid[0:grid_size, 0:grid_size]
    if cfg["pattern"] == "clustered":
        signal = np.exp(-((x-grid_size*0.72)**2 + (y-grid_size*0.32)**2)/(2*(grid_size*.19)**2))
    elif cfg["pattern"] == "diffuse":
        signal = .45 + .22*np.sin(x/1.7) + .14*np.cos(y/2.1)
    elif cfg["pattern"] == "sparse":
        signal = np.exp(-((x-grid_size*.25)**2 + (y-grid_size*.72)**2)/(2*(grid_size*.10)**2))
    else:
        signal = np.full_like(x, .03, dtype=float)
    signal = np.clip(signal + rng.normal(0, .06, size=signal.shape), 0, 1)
    threshold = np.quantile(signal, 1-cfg["positive_fraction"])
    label = (signal >= threshold).astype(int)
    embedding = np.clip(.15 + .70*signal + rng.normal(0, .08, size=signal.shape), 0, 1)
    tissue = np.clip(.6 + rng.normal(0, .16, size=signal.shape), 0.05, 1)
    return pd.DataFrame({"x":x.ravel(),"y":y.ravel(),"signal":signal.ravel(),"embedding_score":embedding.ravel(),"tissue_quality":tissue.ravel(),"tile_label":label.ravel()})

def aggregate(scores: np.ndarray, method: str, temperature: float = 7.0):
    scores=np.asarray(scores,dtype=float)
    if method == "Mean pooling":
        weights=np.full(len(scores),1/len(scores)); value=float(scores.mean())
    elif method == "Max pooling":
        weights=np.zeros(len(scores));weights[int(np.argmax(scores))]=1.0;value=float(scores.max())
    elif method == "Attention pooling":
        z=np.exp((scores-scores.max())*temperature);weights=z/z.sum();value=float(np.sum(weights*scores))
    else: raise ValueError(method)
    return value, weights

def sample_indices(df: pd.DataFrame, method: str, n: int, seed: int = 42) -> np.ndarray:
    n=min(n,len(df)); rng=np.random.default_rng(seed)
    if method == "Random": return np.sort(rng.choice(len(df),size=n,replace=False))
    if method == "Quality weighted":
        p=df.tissue_quality.to_numpy();p=p/p.sum();return np.sort(rng.choice(len(df),size=n,replace=False,p=p))
    # Farthest-point spatial selection, deterministic start at center-nearest.
    pts=df[["x","y"]].to_numpy(float);center=pts.mean(axis=0);chosen=[int(np.argmin(((pts-center)**2).sum(axis=1)))]
    while len(chosen)<n:
        dist=np.min(((pts[:,None,:]-pts[np.array(chosen)][None,:,:])**2).sum(axis=2),axis=1)
        dist[np.array(chosen)]=-1;chosen.append(int(np.argmax(dist)))
    return np.sort(np.array(chosen))
