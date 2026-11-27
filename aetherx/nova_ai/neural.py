# -*- coding: utf-8 -*-
"""
NOVA SİNİR AĞI — niyet sınıflandırıcı (numpy ile yazılmış küçük çok katmanlı algılayıcı).
  girdi  : 1024 boyutlu karma (hash) özellik vektörü — sözcükler, Türkçe kökler, harf üçlüleri (L2 normalize)
  gizli  : 48 nöron, tanh
  çıktı  : niyet sayısı kadar nöron, softmax → her niyet için olasılık
Eğitim verisi engine.INTENT_WORDS, kavram/rehber sözlükleri ve gök cismi adlarından kurallı artırmayla üretilir
(sabit tohum → her açılışta aynı ağ). Eğitim Adam ile tam toplu yapılır; masaüstünde ~1 sn sürer, bir kez yapılır.
Kural tabanlı eşleştirici ile birlikte çalışır: kurallar net bir şey bulamazsa ya da ağ çok farklı bir şeyden
eminse ağın kararı kullanılır; olasılık değeri NOVA'nın "ne kadar eminim" ifadesine dönüşür.
Son girdinin gizli katman etkinlikleri (`last_hidden`) AI KONTROL MERKEZİ'nde canlı nöronlar olarak çizilir.
"""
import random
import zlib

import numpy as np

from . import lexicon as LX

DIM = 1024
HID = 48
F32 = np.float32


def _h(s):
    return zlib.crc32(s.encode("utf-8")) % DIM


def features(norm):
    v = np.zeros(DIM, F32)
    toks = LX.tokens(norm)
    for t in toks:
        v[_h("w:" + t)] += 1.0
        st = LX.stem(t)
        if st != t:
            v[_h("s:" + st)] += 0.7
        p = f"#{t}#"
        for i in range(len(p) - 2):
            v[_h("c:" + p[i:i + 3])] += 0.35
    for a, b in zip(toks, toks[1:]):
        v[_h("b:" + a + "_" + b)] += 0.8
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


FILL_TR = ("", "", "nova ", "bana ", "lütfen ", "acaba ", "söyler misin ", "bir şey soracağım ")
FILL_EN = ("", "", "nova ", "please ", "tell me ", "can you tell me ", "hey ", "i wonder ")
TAIL = ("", "", "?", " lütfen", " please", " nova")


def build_dataset(intent_words, extra, bodies, seed=7):
    """(metinler, etiketler, sınıf adları). extra: {niyet: [ifade, ...]} — kavram/rehber/veri niyetleri."""
    rng = random.Random(seed)
    classes = sorted(set(intent_words) | set(extra))
    X, Y = [], []
    body_int = {"gravity", "temp", "day", "year", "distance", "moons", "atmo", "size", "mass", "escape", "missions",
                "hazards", "weight", "jump", "sunlight", "facts", "plan"}
    for ci, c in enumerate(classes):
        phrases = list(intent_words.get(c, ())) + list(extra.get(c, ()))
        for ph in phrases:
            for _ in range(6):
                pre = rng.choice(FILL_TR + FILL_EN)
                txt = pre + ph + rng.choice(TAIL)
                if c in body_int and rng.random() < 0.7:
                    b = rng.choice(bodies)
                    txt = (b + " " + txt) if rng.random() < 0.5 else (txt + " " + b)
                X.append(LX.normalize(txt))
                Y.append(ci)
    return X, np.array(Y), classes


class IntentNet:
    def __init__(self):
        self.classes = None
        self.W1 = self.b1 = self.W2 = self.b2 = None
        self.last_hidden = np.zeros(HID, F32)
        self.last_probs = None
        self.trained = False
        self.train_loss = None
        self.train_acc = None

    def train(self, X, Y, classes, epochs=220, lr=0.02, seed=3):
        rs = np.random.RandomState(seed)
        A = np.stack([features(x) for x in X]).astype(F32)
        self.vocab = {t for x in X for t in LX.tokens(x)} | {LX.stem(t) for x in X for t in LX.tokens(x)}
        n, k = len(A), len(classes)
        W1 = (rs.randn(DIM, HID) * (1.0 / np.sqrt(DIM))).astype(F32)
        b1 = np.zeros(HID, F32)
        W2 = (rs.randn(HID, k) * (1.0 / np.sqrt(HID))).astype(F32)
        b2 = np.zeros(k, F32)
        params = [W1, b1, W2, b2]
        m = [np.zeros_like(p) for p in params]
        v = [np.zeros_like(p) for p in params]
        Yoh = np.eye(k, dtype=F32)[Y]
        b1_, b2_, eps = 0.9, 0.999, 1e-8
        for ep in range(1, epochs + 1):
            Hh = np.tanh(A @ W1 + b1)
            Z = Hh @ W2 + b2
            Z -= Z.max(1, keepdims=True)
            P = np.exp(Z)
            P /= P.sum(1, keepdims=True)
            dZ = (P - Yoh) / n
            gW2 = Hh.T @ dZ + 1e-4 * W2
            gb2 = dZ.sum(0)
            dH = (dZ @ W2.T) * (1 - Hh * Hh)
            gW1 = A.T @ dH + 1e-4 * W1
            gb1 = dH.sum(0)
            for i, (p, g) in enumerate(zip(params, (gW1, gb1, gW2, gb2))):
                m[i] = b1_ * m[i] + (1 - b1_) * g
                v[i] = b2_ * v[i] + (1 - b2_) * g * g
                mh = m[i] / (1 - b1_ ** ep)
                vh = v[i] / (1 - b2_ ** ep)
                p -= lr * mh / (np.sqrt(vh) + eps)
        self.W1, self.b1, self.W2, self.b2 = params
        self.classes = classes
        self.train_loss = float(-np.log(P[np.arange(n), Y] + 1e-9).mean())
        self.train_acc = float((P.argmax(1) == Y).mean())
        self.trained = True

    def predict(self, norm):
        """[(niyet, olasılık), ...] büyükten küçüğe."""
        if not self.trained:
            return []
        toks = LX.tokens(norm)
        known = [t for t in toks if t in self.vocab or LX.stem(t) in self.vocab]
        if not known or len(known) / max(1, len(toks)) < 0.34:
            return []                                  # tanımadığı sözcükler: tahmin yürütmez (softmax her şeye bir sınıf verir)
        x = features(norm)
        h = np.tanh(x @ self.W1 + self.b1)
        z = h @ self.W2 + self.b2
        z -= z.max()
        p = np.exp(z)
        p /= p.sum()
        self.last_hidden = h
        self.last_probs = p
        order = np.argsort(-p)[:5]
        return [(self.classes[i], float(p[i])) for i in order]
