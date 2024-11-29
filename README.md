## wandb-sync
Run Machine/Deep learning model using wandb, and automatically record your experimental data using API.

**🎉  wandb-sync always welcome new contributer 🎉**

**Features**
- Load running data from WandB and automatically record it to Google Spreadsheet, Notion.
- Use ```FIXED_HEADERS``` for your customization. Or wnadb-sync would record all of the data.
- Handle NaN value and special character (ex. ◈, @ )

Following table is example.

| Run ID | Timestamp | User | Model Type | Batch Size | Epochs | Training Loss | Validation Loss |
|--------|-----------|------|------------|---------------|------------|---------|------------|
| 2xk8p9n0 | 2024-11-20 14:30:15 | Namgyu-Youn | ResNet50 | 32 | 100 | 0.245 | 0.312 |
| 7mq2r5v3 | 2024-11-20 15:45:22 | taeyoung1005 | ResNet101 | 64 | 150 | 0.198 | 0.287 |
| 9kt4h8w1 | 2024-11-20 17:20:03 | - | EfficientNet | 8 | 80 | 0.267 | 0.295 |
| 3np6j2x5 | 2024-11-20 19:10:45 | - | VGG16 | 16 | 120 | 0.312 | 0.358 |


## How to use?
### Step 1. Clone the repository.
```bash
git clone https://github.com/Namgyu-Youn/wandb-sync.git
```

<br/>

### Step 2. Install required python libary.
```bash
pip install wandb gspread oauth2client notion_client
```
or
```bash
pip install -r requirements.txt
```
or
run container using docker
```bash
docker build -t wandb-sync
docker run -d --name wandb-sync wandb-sync
```

<br/>

### Step 3. (Optional) Edit ```config.json``` and run the script file
- If you want to use your customized values, then it can be done by editing.
- Following is the example of the ```FIXED_HEADERS```
``` bash
{
    "FIXED_HEADERS": [
      "run_id",
      "_timestamp",
      "train_loss"
      "model_name",
      "batch_size",
      "learning_rate"
    ],
  }
```

<br/>

### Step 4. Run the script file
```bash
python wandb-notion-sync.py --user_name <USER_NAME> --NOTION_CONFIG <PATH>
```
or
```bash
python wandb-gcp-sync.py --user_name <USER_NAME> --GCP_CONFIG <PATH>
```

<br/>


## 📝 Note
- You need your own API(Google spreadsheet or Notion)
- Don't record duplicate run : If ```RUN ID``` exist, then it would be skipped.
- Records only when WandB status is **finished or killed**
- If you want to record your wandB data more often, paid token would be needed. (free for 30min)
- Read more : [Notion API](https://developers.notion.com/reference/database), [Google sheets API](https://developers.google.com/sheets/api/guides/concepts?hl=ko)