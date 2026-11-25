# Out-of-fold estimate with random row folds

KFold(shuffle=True) instead of GroupKFold by customer. Labels come from whole reviewed accounts, so a
customer's frauds sit on both sides of every fold and the GBT recognises the account (card_age_days is
a per-customer constant). The estimate is several times the AP on new customers, and it picks the wrong model.
