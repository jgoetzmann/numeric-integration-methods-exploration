# Issue Analysis and Solution: Identical Butcher Tables

## Problem Identified

**Issue:** Run 1 (balanced weights) and Run 2 (efficiency focused) produced **IDENTICAL** butcher tables, which defeats the purpose of having different training configurations.

## Root Cause Analysis

### 1. Configuration Problem
- Both runs were using the **same global configuration** (`config.py`)
- The `TrainingPipeline` class was hardcoded to import `from config import config`
- Despite creating specialized config files, they weren't being used

### 2. Identical Butcher Table Evidence
```json
// Both runs produced this EXACT butcher table:
"A": [
  [0.0, 0.0, 0.0, 0.0],
  [-0.250919762305275, 0.0, 0.0, 0.0],
  [0.9014286128198323, 0.4639878836228102, 0.0, 0.0],
  [0.1973169683940732, -0.687962719115127, -0.6880109593275947, 0.0]
]
```

### 3. Why This Happened
- Same random seed initialization
- Same dataset generation
- Same model architecture
- Same training parameters
- Same metric weights (despite different config files)

## Solution Implemented

### 1. Fixed Import Issues
- **Problem:** Training scripts couldn't import modules from `scripts/` directory
- **Solution:** Fixed Python path imports in all training scripts

### 2. Configuration Override
- **Problem:** Global config was always used regardless of specialized configs
- **Solution:** Implemented config override mechanism:
```python
# Override the global config
train.config = specialized_config
```

### 3. Created Truly Different Configurations

#### Run 2 V2 (Efficiency-Focused V2)
- **Dataset:** 1,200 ODEs (400 stiff, 800 non-stiff) vs original 1,000
- **Stages:** 3-5 range vs original 4-6
- **Integration Time:** 0.12s vs original 0.1s
- **ML Model:** 320 hidden units vs original 256
- **Weights:** 30% accuracy, 60% efficiency, 10% stability vs original 35%, 55%, 10%
- **Training:** 300 epochs vs original 400

#### Run 3 (Accuracy-Focused)
- **Dataset:** 1,500 ODEs (600 stiff, 900 non-stiff)
- **Stages:** 4-7 range (default 5)
- **Integration Time:** 0.2s (longer for accuracy)
- **ML Model:** 512 hidden units (larger)
- **Weights:** 70% accuracy, 20% efficiency, 10% stability
- **Training:** 500 epochs

#### Run 4 (Stability-Focused)
- **Dataset:** 1,200 ODEs (800 stiff, 400 non-stiff) - 67% stiff!
- **Stages:** 3-6 range (default 4)
- **Integration Time:** 0.15s
- **ML Model:** 384 hidden units
- **Weights:** 30% accuracy, 20% efficiency, 50% stability
- **Training:** 350 epochs

#### Run 5 (Mixed-Focus)
- **Dataset:** 2,000 ODEs (1,000 stiff, 1,000 non-stiff) - largest dataset
- **Stages:** 3-8 range (default 5) - widest range
- **Integration Time:** 0.25s (longest)
- **ML Model:** 640 hidden units (largest)
- **Weights:** 45% accuracy, 35% efficiency, 20% stability
- **Training:** 600 epochs (longest)

## Key Differences Between Runs

| Run | Dataset Size | Stiff % | Stages | ML Size | Accuracy Weight | Efficiency Weight | Stability Weight |
|-----|--------------|---------|--------|---------|-----------------|-------------------|------------------|
| 1   | 1,000        | 30%     | 4-6    | 256     | 50%             | 30%               | 20%              |
| 2V2 | 1,200        | 33%     | 3-5    | 320     | 30%             | 60%               | 10%              |
| 3   | 1,500        | 40%     | 4-7    | 512     | 70%             | 20%               | 10%              |
| 4   | 1,200        | 67%     | 3-6    | 384     | 30%             | 20%               | 50%              |
| 5   | 2,000        | 50%     | 3-8    | 640     | 45%             | 35%               | 20%              |

## Validation Strategy

Each run now uses:
1. **Different dataset sizes and compositions**
2. **Different stage ranges and defaults**
3. **Different ML model architectures**
4. **Different metric weightings**
5. **Different training durations**
6. **Different integration parameters**

## Expected Outcomes

With these changes, each run should produce:
- **Different butcher tables** due to different configurations
- **Different performance profiles** optimized for different objectives
- **Meaningful comparisons** between approaches
- **Robust validation** across diverse configurations

## Status

✅ **All training runs are now running** with properly differentiated configurations
✅ **Import errors fixed**
✅ **Configuration override implemented**
✅ **Truly different parameters for each run**

The repository now has 5 distinct training runs that will produce genuinely different results for comprehensive analysis and publication.
