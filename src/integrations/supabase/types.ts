export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      drivers: {
        Row: {
          code: string
          created_at: string | null
          full_name: string
          id: string
          number: number
          team_id: string | null
          updated_at: string | null
        }
        Insert: {
          code: string
          created_at?: string | null
          full_name: string
          id?: string
          number: number
          team_id?: string | null
          updated_at?: string | null
        }
        Update: {
          code?: string
          created_at?: string | null
          full_name?: string
          id?: string
          number?: number
          team_id?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "drivers_team_id_fkey"
            columns: ["team_id"]
            isOneToOne: false
            referencedRelation: "teams"
            referencedColumns: ["id"]
          },
        ]
      }
      lap_times: {
        Row: {
          created_at: string | null
          driver_id: string | null
          gap: string | null
          id: string
          interval: string | null
          is_personal_best: boolean | null
          is_purple_sector: boolean | null
          lap_number: number
          position: number
          sector1_time: unknown | null
          sector2_time: unknown | null
          sector3_time: unknown | null
          session_id: string | null
          time: unknown | null
        }
        Insert: {
          created_at?: string | null
          driver_id?: string | null
          gap?: string | null
          id?: string
          interval?: string | null
          is_personal_best?: boolean | null
          is_purple_sector?: boolean | null
          lap_number: number
          position: number
          sector1_time?: unknown | null
          sector2_time?: unknown | null
          sector3_time?: unknown | null
          session_id?: string | null
          time?: unknown | null
        }
        Update: {
          created_at?: string | null
          driver_id?: string | null
          gap?: string | null
          id?: string
          interval?: string | null
          is_personal_best?: boolean | null
          is_purple_sector?: boolean | null
          lap_number?: number
          position?: number
          sector1_time?: unknown | null
          sector2_time?: unknown | null
          sector3_time?: unknown | null
          session_id?: string | null
          time?: unknown | null
        }
        Relationships: [
          {
            foreignKeyName: "lap_times_driver_id_fkey"
            columns: ["driver_id"]
            isOneToOne: false
            referencedRelation: "drivers"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lap_times_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      sessions: {
        Row: {
          circuit: string
          created_at: string | null
          current_lap: number | null
          end_time: string | null
          id: string
          name: string
          start_time: string
          status: string | null
          total_laps: number | null
          type: Database["public"]["Enums"]["session_type"]
          updated_at: string | null
        }
        Insert: {
          circuit: string
          created_at?: string | null
          current_lap?: number | null
          end_time?: string | null
          id?: string
          name: string
          start_time: string
          status?: string | null
          total_laps?: number | null
          type: Database["public"]["Enums"]["session_type"]
          updated_at?: string | null
        }
        Update: {
          circuit?: string
          created_at?: string | null
          current_lap?: number | null
          end_time?: string | null
          id?: string
          name?: string
          start_time?: string
          status?: string | null
          total_laps?: number | null
          type?: Database["public"]["Enums"]["session_type"]
          updated_at?: string | null
        }
        Relationships: []
      }
      teams: {
        Row: {
          color: string
          created_at: string | null
          id: string
          name: string
        }
        Insert: {
          color: string
          created_at?: string | null
          id?: string
          name: string
        }
        Update: {
          color?: string
          created_at?: string | null
          id?: string
          name?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      session_type:
        | "practice1"
        | "practice2"
        | "practice3"
        | "qualifying"
        | "sprint"
        | "race"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DefaultSchema = Database[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof Database },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof Database },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends { schema: keyof Database }
  ? Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      session_type: [
        "practice1",
        "practice2",
        "practice3",
        "qualifying",
        "sprint",
        "race",
      ],
    },
  },
} as const
