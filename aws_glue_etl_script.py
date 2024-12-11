import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, from_unixtime, regexp_replace, when

def validate_product_id(df):
    """
    Validate product_id to ensure it's not cintains just numbers
    """
    return df.filter(col("product_id").rlike(r'^(?=.*[a-zA-Z])\w+$'))

def transform_purchase_data(datasource0):
    """
    Transform purchase data with requested requirements
    """
    # Convert Unix timestamp to datetime
    df_transformed = datasource0.withColumn(
        "purchase_date", 
        from_unixtime(col("purchase_date").cast("long"))
    )
    
    # Ensure discount is a float with 2 decimal places
    df_transformed = df_transformed.withColumn(
        "discount", 
        when(col("discount").isNotNull(), 
             regexp_replace(col("discount").cast("float"), 
                            "^(\\d+\\.\\d{2}).*$", "$1").cast("float"))
        .otherwise(0.0)
    )
    
    # Validate and filter product_id
    df_transformed = validate_product_id(df_transformed)
    
    return df_transformed

def main():
    # Initialize Glue Context
    glueContext = GlueContext(SparkContext.getOrCreate())
    spark = glueContext.spark_session
    job = Job(glueContext)
    
    # Get job parameters
    args = getResolvedOptions(sys.argv, ['JOB_NAME', 'input_path', 'output_path'])
    
    # Read input data from S3
    datasource0 = glueContext.create_dynamic_frame.from_catalog(
        database="purchase_data_db",
        table_name="input_purchases"
    )
    
    # Convert to Spark DataFrame
    df = datasource0.toDF()
    
    # Transform data
    df_transformed = transform_purchase_data(df)
    
    # Write to Redshift
    glueContext.write_dynamic_frame.from_jdbc_conf(
        frame=DynamicFrame.fromDF(df_transformed, glueContext),
        catalog_connection="redshift_connection",
        connection_options={
            "dbtable": "purchase_data",
            "database": "purchase_data_rs_dwh"
        }
    )

    job.commit()

if __name__ == "__main__":
    main()