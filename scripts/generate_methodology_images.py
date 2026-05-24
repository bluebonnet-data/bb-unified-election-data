import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

os.makedirs('docs/images', exist_ok=True)

print("Loading data...")
precincts = gpd.read_file('data/processed/travis_precincts_2020.gpkg')
districts = gpd.read_file('data/processed/travis_districts_2026.gpkg')
blocks = gpd.read_file('data/processed/travis_blocks_2020.gpkg')
results = pd.read_csv('data/processed/travis_interpolated_results.csv')

# Image 1 — Travis County map: precincts vs districts
print("Generating map...")
fig, ax = plt.subplots(1, 1, figsize=(10, 8))
precincts.plot(ax=ax, color='#E6F1FB', edgecolor='#185FA5', linewidth=0.4)
districts.plot(ax=ax, color='none', edgecolor='#E24B4A', linewidth=2)
ax.set_title('Travis County: 2020 voting precincts vs 2026 congressional district boundaries', 
             fontsize=11, pad=12)
ax.set_axis_off()
blue_patch = mpatches.Patch(color='#E6F1FB', label='2020 precincts (247 total)')
red_patch = mpatches.Patch(color='#E24B4A', label='2026 congressional districts (7 touch Travis County)')
ax.legend(handles=[blue_patch, red_patch], loc='lower right', fontsize=9)
plt.tight_layout()
plt.savefig('docs/images/travis_county_map.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved travis_county_map.png")

# Image 2 — Population density
print("Generating population density map...")
fig, ax = plt.subplots(1, 1, figsize=(10, 8))
blocks['total'] = pd.to_numeric(blocks['total'], errors='coerce')
blocks.plot(ax=ax, column='total', cmap='YlOrRd', edgecolor='none', legend=True,
            legend_kwds={'label': 'Population per census block', 'shrink': 0.6})
ax.set_title('Travis County 2020: population density by census block', fontsize=11, pad=12)
ax.set_axis_off()
plt.tight_layout()
plt.savefig('docs/images/population_density.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved population_density.png")

# Image 3 — District results bar chart
print("Generating results chart...")
biden = results[results['candidate'] == 'Biden'].set_index('new_district_id')['estimated_votes']
trump = results[results['candidate'] == 'Trump'].set_index('new_district_id')['estimated_votes']
districts_list = sorted(biden.index)

fig, ax = plt.subplots(figsize=(10, 6))
y = range(len(districts_list))
bar_height = 0.35
ax.barh([i + bar_height/2 for i in y], 
        [biden[d] for d in districts_list], 
        bar_height, label='Biden (D)', color='#185FA5')
ax.barh([i - bar_height/2 for i in y], 
        [trump[d] for d in districts_list], 
        bar_height, label='Trump (R)', color='#A32D2D')
ax.set_yticks(list(y))
ax.set_yticklabels([f'District {d}' for d in districts_list])
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x/1000)}K'))
ax.set_title('Estimated 2020 presidential results by 2026 congressional district\n(Travis County contributions only)', 
             fontsize=11, pad=12)
ax.legend(fontsize=10)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig('docs/images/district_results.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved district_results.png")

print("\nAll images generated successfully.")