# Confirmatory analysis — outputs/confirm/final

Participants analyzed: 100/100 (missing main reads: {'opus': [], 'gpt': []})

## Primary: noninferiority of sensitivity for any CAC vs DeepCAC (margin -10 points; 97.5% CI)

- Claude Opus 5.5: sensitivity diff 0.0 points (97.5% CI -8.2, 8.2; 95% CI -6.8, 6.8) -> NONINFERIOR; specificity diff -12.0 (97.5% CI -33.4, 10.9) -> noninferiority NOT shown
- GPT (gpt-6-astra): sensitivity diff -4.0 points (97.5% CI -12.2, 2.3; 95% CI -10.8, 1.2) -> noninferiority NOT shown; specificity diff -4.0 (97.5% CI -29.5, 22.1) -> noninferiority NOT shown

## Readers

- opus: sens 72/75, spec 16/25, >=100 sens 42/50 spec 40/50, wkappa 0.804 (0.725, 0.870), exact 62/100, by stratum {'0': '9/25', '1-100': '23/25', '101-300': '24/25', '>300': '25/25'}
- gpt: sens 69/75, spec 18/25, >=100 sens 46/50 spec 42/50, wkappa 0.845 (0.778, 0.894), exact 65/100, by stratum {'0': '7/25', '1-100': '20/25', '101-300': '24/25', '>300': '25/25'}
- deepcac: sens 72/75, spec 19/25, >=100 sens 46/50 spec 46/50, wkappa 0.884 (0.825, 0.929), exact 75/100, by stratum {'0': '6/25', '1-100': '22/25', '101-300': '25/25', '>300': '25/25'}

## Secondary

{
 "opus": {
  "sig_sens_vs_deepcac": {
   "x_only": 3,
   "y_only": 7,
   "p": 0.34375
  },
  "sig_spec_vs_deepcac": {
   "x_only": 1,
   "y_only": 7,
   "p": 0.0703125
  },
  "wkappa_diff": -0.08013085399449027,
  "wkappa_diff_ci95": [
   -0.15165778346277917,
   -0.016824561626745463
  ]
 },
 "gpt": {
  "sig_sens_vs_deepcac": {
   "x_only": 3,
   "y_only": 3,
   "p": 1.0
  },
  "sig_spec_vs_deepcac": {
   "x_only": 2,
   "y_only": 6,
   "p": 0.2890625
  },
  "wkappa_diff": -0.03960055096418724,
  "wkappa_diff_ci95": [
   -0.11193092822696935,
   0.030493175075563955
  ]
 }
}

## Reliability

{
 "opus": {
  "studies": 20,
  "reads": 100,
  "incomplete_studies": [],
  "per_read_sens": {
   "k": 75,
   "n": 75,
   "ci95": [
    0.9512761567859911,
    1.0000000000000002
   ]
  },
  "per_read_spec": {
   "k": 15,
   "n": 25,
   "ci95": [
    0.4073945721749423,
    0.7659669772729795
   ]
  },
  "discordant_presence": {
   "0": 0,
   "1-100": 0,
   "101-300": 0,
   ">300": 0
  },
  "same_category_all_reads": {
   "0": 5,
   "1-100": 3,
   "101-300": 2,
   ">300": 3
  },
  "reads_correct_category": 63,
  "alpha": 1.0,
  "alpha_ci95": [
   1.0,
   1.0
  ]
 },
 "gpt": {
  "studies": 20,
  "reads": 100,
  "incomplete_studies": [],
  "per_read_sens": {
   "k": 72,
   "n": 75,
   "ci95": [
    0.8888701283966873,
    0.9863039358464244
   ]
  },
  "per_read_spec": {
   "k": 10,
   "n": 25,
   "ci95": [
    0.23403302272702053,
    0.5926054278250577
   ]
  },
  "discordant_presence": {
   "0": 0,
   "1-100": 2,
   "101-300": 0,
   ">300": 0
  },
  "same_category_all_reads": {
   "0": 5,
   "1-100": 3,
   "101-300": 4,
   ">300": 5
  },
  "reads_correct_category": 52,
  "alpha": 0.7811671087533156,
  "alpha_ci95": [
   0.05842391304347827,
   1.0
  ]
 }
}

## Confidence

{
 "opus": {
  "strata": {
   "HIGH": {
    "n": 4,
    "acc4": 4,
    "ci95": [
     0.5101091596030786,
     0.9999999999999999
    ],
    "presence_correct": 4
   },
   "MEDIUM": {
    "n": 65,
    "acc4": 43,
    "ci95": [
     0.5403837681802639,
     0.7646649675853523
    ],
    "presence_correct": 62
   },
   "LOW": {
    "n": 31,
    "acc4": 15,
    "ci95": [
     0.31970251448435416,
     0.651596046709453
    ],
    "presence_correct": 22
   }
  },
  "missed_by_conf": {
   "LOW": 1,
   "MEDIUM": 2
  },
  "fp_by_conf": {
   "LOW": 8,
   "MEDIUM": 1
  }
 },
 "gpt": {
  "strata": {
   "HIGH": {
    "n": 26,
    "acc4": 22,
    "ci95": [
     0.6646880050648342,
     0.9384996631922973
    ],
    "presence_correct": 24
   },
   "MEDIUM": {
    "n": 74,
    "acc4": 43,
    "ci95": [
     0.4674028436242695,
     0.6867566514887312
    ],
    "presence_correct": 63
   }
  },
  "missed_by_conf": {
   "MEDIUM": 4,
   "HIGH": 2
  },
  "fp_by_conf": {
   "MEDIUM": 7
  }
 }
}

## Sensitivity analyses

{
 "sternotomy_both_models": [
  "209249",
  "119485",
  "115992"
 ],
 "excl_sternotomy": {
  "opus": {
   "sens": {
    "diff": 0.0,
    "lo": -0.08484347187098341,
    "hi": 0.08484347187098341,
    "a": 67,
    "b": 2,
    "c": 2,
    "d": 1,
    "n": 72
   },
   "spec": {
    "diff": -0.12,
    "lo": -0.3341809275113015,
    "hi": 0.10886079735225576,
    "a": 14,
    "b": 2,
    "c": 5,
    "d": 4,
    "n": 25
   }
  },
  "gpt": {
   "sens": {
    "diff": -0.04166666666666674,
    "lo": -0.1269126543999089,
    "hi": 0.023972242112928505,
    "a": 66,
    "b": 0,
    "c": 3,
    "d": 3,
    "n": 72
   },
   "spec": {
    "diff": -0.040000000000000036,
    "lo": -0.2945411896799652,
    "hi": 0.22102242047550752,
    "a": 14,
    "b": 4,
    "c": 5,
    "d": 2,
    "n": 25
   }
  }
 }
}