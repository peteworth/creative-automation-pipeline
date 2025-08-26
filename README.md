# Creative Automation Pipeline

An automated system for processing campaign briefs and generating marketing assets using Adobe Firefly for image generation, AWS S3 for storage, and Bannerbear for asset composition.

## Overview

This pipeline automates the creative asset production workflow by:
1. Processing JSON campaign briefs placed in a START folder
2. Managing hero images using intelligent naming conventions or generating them with Adobe Firefly
3. Creating multiple asset variations using Bannerbear templates
4. Organizing outputs in structured campaign folders
5. Storing all assets in AWS S3 for reliable access

## Prerequisites

### Required Services & Accounts

You'll need active accounts and API access for:

- **Adobe Creative SDK** (for Firefly image generation)
- **AWS Account** (for S3 storage)
- **Bannerbear Account** (for asset composition)

### Technical Requirements

- Python 3.8+
- pip (Python package installer)

## Setup Instructions

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/peteworth/creative-automation-pipeline.git
cd creative-automation-pipeline
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root with your API credentials (I pushed an env file with similar dummy data to below already; you'll still need to provide the values but the data for the keys are in there):

```env
# Adobe API Credentials
ADOBE_CLIENT_ID=Provide Key
ADOBE_CLIENT_SECRET=Provide Client Secret

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=Provide AWS Access Key
AWS_SECRET_ACCESS_KEY=Provide AWS Secret Access Key
AWS_S3_BUCKET=Provide Bucket Name
AWS_REGION=us-east-1

# Bannerbear API Configuration
BANNERBEAR_API_KEY=Provide Bannerbear Project API Key
BANNERBEAR_COLLECTION_ID=Provide Collection ID (Reach out to Pete to share this)

# Application Settings
DEBUG_MODE=true
MOCK_MODE=false
```

### 3. Service Setup Details

#### AWS S3 Setup
1. Create an AWS account and S3 bucket
2. Set up IAM user with S3 permissions
3. Note your bucket name and region
4. Ensure your bucket allows public read access for generated URLs

#### Adobe Firefly Setup
1. Visit [Adobe Developer Console](https://developer.adobe.com/)
2. Create a new project
3. Add Firefly API to your project
4. Generate Oauth credentials

#### Bannerbear Setup
1. Create a [Bannerbear account](https://www.bannerbear.com/)
2. Create a new project
3. Set up a Collection with your template designs (I will send a link to an existing collection that can be used)
4. Copy your Collection ID from the Bannerbear dashboard
5. Generate an API key from your account settings - a project API key is enough

**Important**: You'll need to share your Bannerbear Collection ID with team members who want to use the same templates.

### 4. Project Structure

The pipeline will create this folder structure:

```
creative-automation-pipeline/
├── START/                    # Place campaign briefs and hero images here
├── config/
│   └── settings.py
├── src/
│   ├── asset_manager.py
│   ├── bannerbear_composer.py
│   ├── brief_processor.py
│   ├── firefly_generator.py
│   ├── folder_manager.py
│   └── utils.py
├── logs/                     # Generated automatically
├── [campaign_name]/          # Generated per campaign
│   ├── input/
│   └── output/
│       └── [product_name]/
├── main.py
├── .env
└── requirements.txt
```

## Usage

### Campaign Brief Format

Create a JSON file in the START folder with this structure:

```json
{
  "campaign": "Creative Automation Test Campaign",
  "target_region": "en-US",
  "target_audience": "Milennials", 
  "product": [
    "Headphones",
    "Tophat"
  ],
  "campaign_message": "Dream it. Type it. See it. Generate products via AI",
  "file_format": "PNG"
}
```

#### Required Fields:
- **campaign**: Campaign name (used for folder naming)
- **target_region**: Locale code (e.g., "en-US", "fr-FR") for region-aware image generation (this fills the prompt bias; if not provided then en-US will be default)
- **target_audience**: Description of target audience
- **product**: Array of product names (minimum 2 products)
- **campaign_message**: Text to appear on generated assets
- **file_format**: "PNG", "JPEG", or "JPG"

### Hero Image Handling

The pipeline uses intelligent image detection with this priority:

1. **Naming Convention** (Recommended): Place images in START folder using pattern:
   ```
   campaignname_productname_hero.jpg ie Creative_Automation_Test_Campaign_Headpones_hero.png
   ```

2. **Automatic Generation**: If no image found, generates one using Adobe Firefly

3. **S3 Existing Assets**: Checks for previously uploaded assets

### Running the Pipeline

1. Place campaign brief JSON and any hero images in the START folder
2. Run the pipeline:
   ```bash
   python main.py
   ```
3. Monitor the console output and logs/pipeline.log for progress
4. Find generated assets in the campaign output folders

### Output Structure

For each campaign, you'll get:

```
[campaign_name]/
├── input/
│   ├── campaign_brief.json    # Archived brief
│   └── [hero_images]          # Input assets
└── output/
    ├── [product_1]/
    │   ├── 1080x1080_campaign_product.png
    │   ├── 1920x1080_campaign_product.png
    │   └── [other_dimensions]
    └── [product_2]/
        └── [generated_assets]
```

## Features

### Automated Asset Management
- Intelligent hero image detection using naming conventions
- S3 integration for reliable asset storage and sharing
- Automatic fallback to AI-generated images when needed

### Multi-Product Support
- Processes multiple products per campaign brief
- Generates separate asset sets for each product
- Maintains organized folder structure

### Error Handling & Recovery
- Comprehensive logging to logs/pipeline.log
- Graceful failure handling per product/campaign
- Files remain in START folder if processing fails

### Flexible Image Handling
- Support for multiple image formats (PNG, JPEG, JPG)
- Region-aware image generation using target_region
- Automatic image format conversion based on campaign preferences

## Troubleshooting

### Common Issues

**"Environment validation failed"**
- Check that all required variables are set in .env file
- Verify API credentials are valid and active

**"Hero image not found"**
- Ensure image files use correct naming convention
- Check that files are in START folder
- Verify file extensions are supported (.jpg, .png, etc.)

**"Bannerbear API error"**
- Confirm your Collection ID is correct
- Verify API key has proper permissions
- Check that Collection templates are properly configured

**"Adobe access token failed"**
- Verify Adobe Client ID and Secret
- Ensure Firefly API access is approved for your account
- Check Adobe Developer Console for service status

### Debug Mode

Enable debug mode in .env for verbose logging:
```env
DEBUG_MODE=true
```

### Test Connections

You can test individual service connections by running specific modules:

```python
# Test Bannerbear connection
from src.bannerbear_composer import BannerbearComposer
composer = BannerbearComposer()
composer.test_bannerbear_connection()
```

