#!/usr/bin/env node

// Simple test script to verify Azure SQL connection
import * as dotenv from 'dotenv';
import sql from 'mssql';

dotenv.config({ path: '.env.contoso-example' });

async function testConnection() {
  try {
    console.log('Testing connection to Azure SQL Database...');
    console.log(`Server: ${process.env.SERVER_NAME}`);
    console.log(`Database: ${process.env.DATABASE_NAME}`);
    console.log(`User: ${process.env.SQL_USER}`);
    
    const config = {
      server: process.env.SERVER_NAME,
      database: process.env.DATABASE_NAME,
      user: process.env.SQL_USER,
      password: process.env.SQL_PASSWORD,
      options: {
        encrypt: true,
        trustServerCertificate: process.env.TRUST_SERVER_CERTIFICATE?.toLowerCase() === 'true'
      },
      connectionTimeout: (process.env.CONNECTION_TIMEOUT ? parseInt(process.env.CONNECTION_TIMEOUT, 10) : 30) * 1000
    };
    
    const pool = await sql.connect(config);
    console.log('✅ Successfully connected to Azure SQL Database!');
    
    // Test a simple query
    const result = await pool.request().query('SELECT @@VERSION as version, DB_NAME() as database_name');
    console.log('✅ Database version:', result.recordset[0].version.substring(0, 50) + '...');
    console.log('✅ Connected to database:', result.recordset[0].database_name);
    
    // List tables
    const tables = await pool.request().query(`
      SELECT TABLE_SCHEMA, TABLE_NAME 
      FROM INFORMATION_SCHEMA.TABLES 
      WHERE TABLE_TYPE = 'BASE TABLE'
      ORDER BY TABLE_SCHEMA, TABLE_NAME
    `);
    
    console.log(`✅ Found ${tables.recordset.length} tables in the database:`);
    tables.recordset.forEach(table => {
      console.log(`   - ${table.TABLE_SCHEMA}.${table.TABLE_NAME}`);
    });
    
    await pool.close();
    console.log('✅ Connection test completed successfully!');
    
  } catch (error) {
    console.error('❌ Connection failed:', error.message);
    if (error.code) {
      console.error('❌ Error code:', error.code);
    }
    if (error.originalError) {
      console.error('❌ Original error:', error.originalError.message);
    }
  }
}

testConnection();