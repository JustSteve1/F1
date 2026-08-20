# Notebooks

## `seed_fastf1_cache_colab.ipynb`

One-shot **FastF1 → GCS cache seeder** for Colab or local Jupyter.

Cloud Run / GCE cannot download F1 livetiming (datacenter IP soft-fail). Run this notebook on Colab or a laptop, then retry the import job.

### Open in Colab

After this branch is on GitHub:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JustSteve1/F1/blob/cursor/fastf1-seed-colab-notebook-5e79/notebooks/seed_fastf1_cache_colab.ipynb)

Or paste:

```text
https://colab.research.google.com/github/JustSteve1/F1/blob/cursor/fastf1-seed-colab-notebook-5e79/notebooks/seed_fastf1_cache_colab.ipynb
```

### Local Jupyter

```bash
pip install fastf1==3.8.3 google-cloud-storage pandas numpy
gcloud auth application-default login
jupyter notebook notebooks/seed_fastf1_cache_colab.ipynb
```
