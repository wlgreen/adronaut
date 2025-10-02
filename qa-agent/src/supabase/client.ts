import { createClient, SupabaseClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';

dotenv.config();

export interface Database {
  public: {
    Tables: {
      projects: {
        Row: {
          id: string;
          name: string;
          description?: string;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          description?: string;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          description?: string;
          updated_at?: string;
        };
      };
      strategy_versions: {
        Row: {
          id: string;
          project_id: string;
          version: number;
          content: any;
          created_at: string;
        };
        Insert: {
          id?: string;
          project_id: string;
          version: number;
          content: any;
          created_at?: string;
        };
        Update: {
          id?: string;
          project_id?: string;
          version?: number;
          content?: any;
        };
      };
      patches: {
        Row: {
          id: string;
          project_id: string;
          run_id?: string;
          source: 'insights' | 'reflection';
          status: 'proposed' | 'approved' | 'rejected';
          diff: any;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          project_id: string;
          run_id?: string;
          source: 'insights' | 'reflection';
          status?: 'proposed' | 'approved' | 'rejected';
          diff: any;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          status?: 'proposed' | 'approved' | 'rejected';
          updated_at?: string;
        };
      };
      briefs: {
        Row: {
          id: string;
          project_id: string;
          strategy_version_id: string;
          content: any;
          created_at: string;
        };
        Insert: {
          id?: string;
          project_id: string;
          strategy_version_id: string;
          content: any;
          created_at?: string;
        };
      };
      campaigns: {
        Row: {
          id: string;
          project_id: string;
          strategy_id: string;
          name: string;
          content: any;
          created_at: string;
        };
        Insert: {
          id?: string;
          project_id: string;
          strategy_id: string;
          name: string;
          content: any;
          created_at?: string;
        };
      };
      metrics: {
        Row: {
          id: string;
          project_id: string;
          campaign_id?: string;
          bucket: string;
          ctr?: number;
          cpa?: number;
          roas?: number;
          created_at: string;
        };
        Insert: {
          id?: string;
          project_id: string;
          campaign_id?: string;
          bucket: string;
          ctr?: number;
          cpa?: number;
          roas?: number;
          created_at?: string;
        };
      };
      events: {
        Row: {
          id: string;
          event_id: string;
          type: string;
          project_id: string;
          data: any;
          created_at: string;
        };
        Insert: {
          id?: string;
          event_id: string;
          type: string;
          project_id: string;
          data: any;
          created_at?: string;
        };
      };
    };
  };
}

class SupabaseClientSingleton {
  private static instance: SupabaseClient<Database> | null = null;

  public static getInstance(): SupabaseClient<Database> {
    if (!this.instance) {
      const supabaseUrl = process.env.SUPABASE_URL;
      const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

      if (!supabaseUrl || !supabaseServiceRoleKey) {
        throw new Error(
          'Missing required environment variables: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY'
        );
      }

      this.instance = createClient<Database>(supabaseUrl, supabaseServiceRoleKey, {
        auth: {
          autoRefreshToken: false,
          persistSession: false,
        },
      });
    }

    return this.instance;
  }

  public static reset(): void {
    this.instance = null;
  }
}

export const supabase = SupabaseClientSingleton.getInstance();
export default supabase;