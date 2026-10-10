import time
import generator
import optimizer
import baseline
import pandas as pd
import missions
import priority

t0 = time.time()
missions_df = pd.DataFrame(missions.DEFAULT_CLASSES)
shares = missions.get_class_shares("Balanced", missions_df)
df_passes = generator.generate_passes(50, 10, 42, missions_df, shares)
df_passes = priority.apply_aging(df_passes, 0.5)
t1 = time.time()
print(f"Generate passes: {t1 - t0:.3f}s. {len(df_passes)} passes.")

df_fcfs = baseline.schedule_fcfs(df_passes)
t2 = time.time()
print(f"FCFS: {t2 - t1:.3f}s")

df_opt = optimizer.schedule_optimized(df_passes, iterations=1000)
t3 = time.time()
print(f"Opt 1000: {t3 - t2:.3f}s")

optimizer.validate_schedule(df_opt, df_passes)
t4 = time.time()
print(f"Validate: {t4 - t3:.3f}s")

print("Done")
