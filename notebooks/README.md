# Notebooks

## `seed_fastf1_cache_colab.ipynb`

One-shot **FastF1 → GCS cache seeder** for Colab or local Jupyter.

Cloud Run / GCE cannot download F1 livetiming (datacenter IP soft-fail). Run this notebook on Colab or a laptop, then retry the import job.

### Open in Colab

This repo is **private**, and the branch name contains a `/`, so the plain
`colab.research.google.com/github/.../blob/cursor/...` badge URL breaks
(Colab treats `cursor` as the ref and 404s).

**Option A — recommended (private repo):**

1. Open [Google Colab](https://colab.research.google.com/)
2. **File → Open notebook → GitHub**
3. Authorize GitHub if prompted
4. Repo: `JustSteve1/F1`
5. Branch: `cursor/fastf1-seed-colab-notebook-5e79`
6. Open `notebooks/seed_fastf1_cache_colab.ipynb`

**Option B — upload the file:**

1. Download from GitHub:  
   https://github.com/JustSteve1/F1/blob/cursor/fastf1-seed-colab-notebook-5e79/notebooks/seed_fastf1_cache_colab.ipynb  
   (use **Download raw file**)
2. Colab → **File → Upload notebook**

**Option C — encoded branch URL** (may still 404 while the repo is private):

```text
https://colab.research.google.com/github/JustSteve1/F1/blob/cursor%2Ffastf1-seed-colab-notebook-5e79/notebooks/seed_fastf1_cache_colab.ipynb
```

### Local Jupyter

```bash
git fetch origin cursor/fastf1-seed-colab-notebook-5e79
git checkout cursor/fastf1-seed-colab-notebook-5e79
pip install fastf1==3.8.3 google-cloud-storage pandas numpy
gcloud auth application-default login
jupyter notebook notebooks/seed_fastf1_cache_colab.ipynb
```
