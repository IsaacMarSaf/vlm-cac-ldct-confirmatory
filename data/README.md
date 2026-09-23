# data/

| File | Contents |
|---|---|
| `confirm_100_pids.public.csv` | The frozen participant list, in the frozen row order, without the `CAC_manual` and `CAC_AI` columns. It has the PID, stratum (the binned manual score), selected series (UID, section thickness, kernel, instances, size), and reliability-subset flag |
| `main_100_pids.csv`, `pilot_5_pids.csv` | Identifiers of the 105 participants used before (pilot and protocol development), sorted by PID. `scripts/52` excludes them from sampling |
| `reference_hashes.json` | Hashes of the reference file and of the frozen participant list |

## The reference file (not redistributed)

`scripts/52`, `55`, `60`, and `61` read `data/Results_NLST.csv`. It lists 396 NLST participants with the expert manual
Agatston score (`CAC_manual`, the reference standard) and the DeepCAC prediction (`CAC_AI`, the comparator). It comes from
the Source Data provided with Zeleznik R, Foldyna B, Eslami P, et al. *Deep convolutional neural networks to predict
cardiovascular risk from computed tomography.* Nat Commun 2021;12(1):715. doi:10.1038/s41467-021-20966-2.

To obtain it, download the article's Source Data file. Take the NLST participant identifier, the DeepCAC-predicted
Agatston score, and the manually measured Agatston score of the 396 NLST participants, and save them as
`data/Results_NLST.csv` with the header `PID,CAC_AI,CAC_manual`, one row per participant, and LF line endings. The exact sheet
and column names of the Source Data file were not recorded, so verify your copy against the file used in the study:

- 396 data rows;
- SHA-256 `c50d0acd1becadfeb6eb718fa92ba05dd3e794d70417d66bbc969a3bb6030e6d` (LF line endings);
- git blob id `e4851f2e5f7b6fdb70b97ee99c2524f7655c51e8`, the id recorded in the frozen commit.

Then run `python tools/rehydrate_frozen_sample.py` from the repository root. It checks the file and rebuilds
`data/confirm_100_pids.csv`, which is byte-identical to the frozen list (git blob id `afd92cd50fb8b39736e7f3092e4b63db2ea6d972`).
A copy with different formatting but the same values still rebuilds the frozen list, because values are parsed as numbers.

The protocol (section 3) also records the SHA-256 of the sorted participant list:
`af056ff026aa084cca0fac49bd3cbea1619607669b0eeeaf0256f42c2b6b4943`. It is the SHA-256 of the PIDs as strings, sorted and joined
by commas with no final newline. You can check it from the public list alone; `provenance/verify_freeze.py` does so.
