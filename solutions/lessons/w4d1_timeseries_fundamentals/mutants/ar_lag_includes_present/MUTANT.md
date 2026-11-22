# AR design matrix shifted by one row

The lag columns are built as x[p-k+1 : n-k+1], so the 'first lag' is the value being forecast.
Fit looks spectacular (coefficient 1 on the present, residuals near zero) and every prediction uses
information it would not have at forecast time.
