=IF(N2="Glibenclamide", ON, IF(N2="Insulin", "Metformin ", IF(N2="Sitagliptin", N2, "")))
=IF(O2="Insulin", "Insulinshortacting", IF(O2="Mixtard Insulin", "Insulinlongacting ", ""))
=IF(N2="Insulin", "Insulinshortacting", IF(N2="Mixtard Insulin", "Insulinlongacting ", ""))

=IF(N2="Insulin", "Insulinshortacting", IF(N2="Mixtard Insulin", "Insulinlongacting", IF(N2="M Insulin", "Insulinlongacting", "")))
=IF(O2="Insulin", "Insulinshortacting", IF(O2="Mixtard Insulin", "Insulinlongacting", IF(O2="M Insulin", "Insulinlongacting", "")))
=IF(OR(A2="Glibenclamide", A2="Insulin", A2="Metformin", A2="Sitagliptin"), A2, "")

=IF(C2="yes", true, IF(C2="no", false, ""))
34672
=IF(OR(N2="Amlodipine", N2="Atenolol", N2="Captopril", N2="Carvedilol", N2="Hydralazine", N2="Lisinopril", N2="Losartan", N2="Methyldopa", N2="Aspirin", N2="Atorvastatin", N2="Diltiazem", N2="Enalapril maleate", N2="Glyceryl trinitrate", N2="Hydrochlorothiazide", N2="ISMN", N2="Nifedipine", N2="Prazosin", N2="Propranolol", N2="Spironolactone"), N2, "")
=IF(OR(A2="Amlodipine", O2="Atenolol", O2="Captopril", O2="Carvedilol", O2="Hydralazine", O2="Lisinopril", O2="Losartan", O2="Methyldopa", O2="Aspirin", O2="Atorvastatin", O2="Diltiazem", O2="Enalapril maleate", O2="Glyceryl trinitrate", O2="Hydrochlorothiazide", O2="ISMN", O2="Nifedipine", O2="Prazosin", O2="Propranolol", O2="Spironolactone"), O2, "")

