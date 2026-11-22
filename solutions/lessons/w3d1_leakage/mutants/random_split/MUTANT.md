# Mutant: random_split

Cleans the columns and the duplicates but keeps the inherited random split. Invoices of the same customer and month share a cash-flow shock, so a random split puts siblings of test invoices into training; the model will only ever score later invoices.
