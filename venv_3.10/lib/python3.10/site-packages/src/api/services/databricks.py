import pandas as pd
from databricks import sql
from databricks.sdk import WorkspaceClient
from src.config import Settings

class DatabricksService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = WorkspaceClient(host=settings.databricks_host, token=settings.databricks_token)
    
    def _connect(self):
        return sql.connect(
            server_hostname=self.settings.databricks_host.replace("https://", ""),
            http_path=f"/sql/1.0/warehouses/{self.settings.databricks_warehouse_id}",
            access_token=self.settings.databricks_token
        )
    
    def _table(self, name: str) -> str:
        return f"{self.settings.databricks_catalog}.{self.settings.databricks_schema}.{name}"
    
    def query(self, sql_query: str) -> pd.DataFrame:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    return pd.DataFrame(cursor.fetchall(), columns=columns)
                return pd.DataFrame()
    
    def execute(self, sql_query: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_query)
    
    def get_patterns(self, filters: dict = None, limit: int = None) -> pd.DataFrame:
        query = f"""
            SELECT 
                product_id,
                product_idx,
                sku,
                name,
                product_category,
                price,
                promotion,
                seasonal,
                primary_pattern AS detected_pattern,
                secondary_pattern,
                base_sales,
                trend_slope,
                CASE WHEN trend_slope > 0 THEN 'increasing' ELSE 'decreasing' END AS trend_direction,
                seasonal_amplitude,
                seasonal_phase,
                volatility,
                spike_probability,
                dip_probability,
                peak_day_of_year,
                peak_month,
                peak_season_description,
                created_at,
                CASE 
                    WHEN primary_pattern = 'slow_trend' THEN 
                        LEAST(1.0, ABS(trend_slope) * 500 + 0.3)
                    WHEN primary_pattern = 'high_volatility' THEN 
                        LEAST(1.0, volatility)
                    WHEN primary_pattern = 'sudden_spike' THEN 
                        LEAST(1.0, COALESCE(spike_probability, 0.3) + 0.2)
                    WHEN primary_pattern = 'sudden_dip' THEN 
                        LEAST(1.0, COALESCE(dip_probability, 0.3) + 0.2)
                    WHEN primary_pattern IN ('fixed_seasonality', 'varying_seasonality') THEN 
                        LEAST(1.0, COALESCE(seasonal_amplitude, 0) * 3 + 0.4)
                    ELSE 
                        0.5
                END AS confidence
            FROM {self._table('pattern_metadata')}
        """
        conditions = []
        
        if filters:
            if filters.get("product_id"):
                conditions.append(f"product_id = '{filters['product_id']}'")
            if filters.get("pattern_type"):
                conditions.append(f"primary_pattern = '{filters['pattern_type']}'")
            if filters.get("category"):
                conditions.append(f"product_category = '{filters['category']}'")
            if filters.get("trend_direction"):
                if filters['trend_direction'] == 'increasing':
                    conditions.append("trend_slope > 0")
                else:
                    conditions.append("trend_slope <= 0")
            if filters.get("min_confidence"):
                min_conf = filters['min_confidence']
                conditions.append(f"""
                    CASE 
                        WHEN primary_pattern = 'slow_trend' THEN 
                            LEAST(1.0, ABS(trend_slope) * 500 + 0.3)
                        WHEN primary_pattern = 'high_volatility' THEN 
                            LEAST(1.0, volatility)
                        WHEN primary_pattern = 'sudden_spike' THEN 
                            LEAST(1.0, COALESCE(spike_probability, 0.3) + 0.2)
                        WHEN primary_pattern = 'sudden_dip' THEN 
                            LEAST(1.0, COALESCE(dip_probability, 0.3) + 0.2)
                        WHEN primary_pattern IN ('fixed_seasonality', 'varying_seasonality') THEN 
                            LEAST(1.0, COALESCE(seasonal_amplitude, 0) * 3 + 0.4)
                        ELSE 0.5
                    END >= {min_conf}
                """)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY confidence DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return self.query(query)
    
    def get_raw_sales(self, product_id: str = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        query = f"SELECT * FROM {self._table('sales_daily_clean')} WHERE 1=1"
        if product_id:
            query += f" AND product_id = '{product_id}'"
        if start_date:
            query += f" AND sale_date >= '{start_date}'"
        if end_date:
            query += f" AND sale_date <= '{end_date}'"
        query += " ORDER BY product_id, sale_date"
        return self.query(query)
    
    def get_forecasts(self, product_id: str) -> pd.DataFrame:
        return self.query(f"SELECT * FROM {self._table('forecasts')} WHERE product_id = '{product_id}' ORDER BY forecast_date")
    
    def trigger_job(self, job_id: str = None, params: dict = None) -> str:
        jid = job_id or self.settings.transform_job_id
        run = self.client.jobs.run_now(job_id=int(jid), job_parameters=params or {})
        return str(run.run_id)
    
    def get_job_status(self, run_id: str) -> dict:
        run = self.client.jobs.get_run(run_id=int(run_id))
        return {
            "status": run.state.life_cycle_state.value,
            "result": run.state.result_state.value if run.state.result_state else None,
            "message": run.state.state_message
        }