"""initial schema

Revision ID: ca53d84340e4
Revises: 
Create Date: 2026-08-31 08:24:04.762723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca53d84340e4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Queue ticket numbers come from a sequence so concurrent intakes cannot
    # collide. Alembic's autogenerate does not emit standalone sequences, so it
    # is created here, before the table whose default calls nextval() on it.
    op.execute("CREATE SEQUENCE IF NOT EXISTS queue_number_seq START WITH 1 INCREMENT BY 1")

    op.create_table('analytics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('snapshot_date', sa.Date(), nullable=False),
    sa.Column('total_patients', sa.Integer(), server_default='0', nullable=False),
    sa.Column('total_triaged', sa.Integer(), server_default='0', nullable=False),
    sa.Column('critical_cases', sa.Integer(), server_default='0', nullable=False),
    sa.Column('urgent_cases', sa.Integer(), server_default='0', nullable=False),
    sa.Column('routine_cases', sa.Integer(), server_default='0', nullable=False),
    sa.Column('avg_wait_time_mins', sa.Float(), server_default='0', nullable=False),
    sa.Column('top_symptom', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('avg_wait_time_mins >= 0', name='ck_analytics_avg_wait_non_negative'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analytics_created_at'), 'analytics', ['created_at'], unique=False)
    op.create_index(op.f('ix_analytics_snapshot_date'), 'analytics', ['snapshot_date'], unique=True)
    op.create_table('doctors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('specialty', sa.String(length=100), nullable=True),
    sa.Column('is_on_duty', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("position('@' in email) > 1", name='ck_doctors_email_shape'),
    sa.CheckConstraint('length(btrim(name)) > 0', name='ck_doctors_name_not_blank'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_doctors_created_at'), 'doctors', ['created_at'], unique=False)
    op.create_index(op.f('ix_doctors_email'), 'doctors', ['email'], unique=True)
    op.create_index(op.f('ix_doctors_is_on_duty'), 'doctors', ['is_on_duty'], unique=False)
    op.create_table('patients',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=False),
    sa.Column('age', sa.Integer(), nullable=True),
    sa.Column('gender', sa.String(length=10), nullable=True),
    sa.Column('location', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('age IS NULL OR (age >= 0 AND age <= 130)', name='ck_patients_age_range'),
    sa.CheckConstraint('length(btrim(name)) > 0', name='ck_patients_name_not_blank'),
    sa.CheckConstraint('length(btrim(phone)) > 0', name='ck_patients_phone_not_blank'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_patients_created_at'), 'patients', ['created_at'], unique=False)
    op.create_index(op.f('ix_patients_location'), 'patients', ['location'], unique=False)
    op.create_index(op.f('ix_patients_phone'), 'patients', ['phone'], unique=False)
    op.create_table('sms_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'SENT', 'FAILED', 'SKIPPED', name='smsstatus'), server_default='PENDING', nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('provider_message_id', sa.String(length=128), nullable=True),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sms_logs_created_at'), 'sms_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_sms_logs_patient_id'), 'sms_logs', ['patient_id'], unique=False)
    op.create_index(op.f('ix_sms_logs_status'), 'sms_logs', ['status'], unique=False)
    op.create_table('symptom_reports',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('raw_input', sa.Text(), nullable=False),
    sa.Column('language_detected', sa.String(length=20), nullable=True),
    sa.Column('symptoms_extracted', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_symptom_reports_created_at'), 'symptom_reports', ['created_at'], unique=False)
    op.create_index(op.f('ix_symptom_reports_language_detected'), 'symptom_reports', ['language_detected'], unique=False)
    op.create_index(op.f('ix_symptom_reports_patient_id'), 'symptom_reports', ['patient_id'], unique=False)
    op.create_table('triage_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('symptom_report_id', sa.Integer(), nullable=False),
    sa.Column('urgency_level', sa.Enum('CRITICAL', 'URGENT', 'ROUTINE', name='urgencylevel'), nullable=False),
    sa.Column('possible_conditions', sa.Text(), nullable=True),
    sa.Column('confidence_score', sa.Float(), nullable=True),
    sa.Column('ai_response_rw', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)', name='ck_triage_results_confidence_range'),
    sa.ForeignKeyConstraint(['symptom_report_id'], ['symptom_reports.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_triage_results_created_at'), 'triage_results', ['created_at'], unique=False)
    op.create_index(op.f('ix_triage_results_symptom_report_id'), 'triage_results', ['symptom_report_id'], unique=True)
    op.create_index(op.f('ix_triage_results_urgency_level'), 'triage_results', ['urgency_level'], unique=False)
    op.create_table('queue',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('triage_result_id', sa.Integer(), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=True),
    sa.Column('queue_number', sa.Integer(), server_default=sa.text("nextval('queue_number_seq')"), nullable=False),
    sa.Column('priority', sa.SmallInteger(), nullable=False),
    sa.Column('status', sa.Enum('WAITING', 'IN_PROGRESS', 'DONE', 'CANCELLED', name='queuestatus'), server_default='WAITING', nullable=False),
    sa.Column('estimated_wait', sa.Integer(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('estimated_wait IS NULL OR estimated_wait >= 0', name='ck_queue_estimated_wait_non_negative'),
    sa.CheckConstraint('priority >= 1 AND priority <= 3', name='ck_queue_priority_range'),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['triage_result_id'], ['triage_results.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('queue_number')
    )
    op.create_index('ix_queue_completed_at', 'queue', ['completed_at'], unique=False)
    op.create_index(op.f('ix_queue_created_at'), 'queue', ['created_at'], unique=False)
    op.create_index(op.f('ix_queue_doctor_id'), 'queue', ['doctor_id'], unique=False)
    op.create_index('ix_queue_live_order', 'queue', ['status', 'priority', 'created_at'], unique=False)
    op.create_index(op.f('ix_queue_priority'), 'queue', ['priority'], unique=False)
    op.create_index(op.f('ix_queue_status'), 'queue', ['status'], unique=False)
    op.create_index(op.f('ix_queue_triage_result_id'), 'queue', ['triage_result_id'], unique=True)
    op.create_table('consultations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('queue_entry_id', sa.Integer(), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('diagnosis', sa.Text(), nullable=True),
    sa.Column('outcome', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['queue_entry_id'], ['queue.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consultations_created_at'), 'consultations', ['created_at'], unique=False)
    op.create_index(op.f('ix_consultations_doctor_id'), 'consultations', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_consultations_outcome'), 'consultations', ['outcome'], unique=False)
    op.create_index(op.f('ix_consultations_queue_entry_id'), 'consultations', ['queue_entry_id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_consultations_queue_entry_id'), table_name='consultations')
    op.drop_index(op.f('ix_consultations_outcome'), table_name='consultations')
    op.drop_index(op.f('ix_consultations_doctor_id'), table_name='consultations')
    op.drop_index(op.f('ix_consultations_created_at'), table_name='consultations')
    op.drop_table('consultations')
    op.drop_index(op.f('ix_queue_triage_result_id'), table_name='queue')
    op.drop_index(op.f('ix_queue_status'), table_name='queue')
    op.drop_index(op.f('ix_queue_priority'), table_name='queue')
    op.drop_index('ix_queue_live_order', table_name='queue')
    op.drop_index(op.f('ix_queue_doctor_id'), table_name='queue')
    op.drop_index(op.f('ix_queue_created_at'), table_name='queue')
    op.drop_index('ix_queue_completed_at', table_name='queue')
    op.drop_table('queue')
    op.drop_index(op.f('ix_triage_results_urgency_level'), table_name='triage_results')
    op.drop_index(op.f('ix_triage_results_symptom_report_id'), table_name='triage_results')
    op.drop_index(op.f('ix_triage_results_created_at'), table_name='triage_results')
    op.drop_table('triage_results')
    op.drop_index(op.f('ix_symptom_reports_patient_id'), table_name='symptom_reports')
    op.drop_index(op.f('ix_symptom_reports_language_detected'), table_name='symptom_reports')
    op.drop_index(op.f('ix_symptom_reports_created_at'), table_name='symptom_reports')
    op.drop_table('symptom_reports')
    op.drop_index(op.f('ix_sms_logs_status'), table_name='sms_logs')
    op.drop_index(op.f('ix_sms_logs_patient_id'), table_name='sms_logs')
    op.drop_index(op.f('ix_sms_logs_created_at'), table_name='sms_logs')
    op.drop_table('sms_logs')
    op.drop_index(op.f('ix_patients_phone'), table_name='patients')
    op.drop_index(op.f('ix_patients_location'), table_name='patients')
    op.drop_index(op.f('ix_patients_created_at'), table_name='patients')
    op.drop_table('patients')
    op.drop_index(op.f('ix_doctors_is_on_duty'), table_name='doctors')
    op.drop_index(op.f('ix_doctors_email'), table_name='doctors')
    op.drop_index(op.f('ix_doctors_created_at'), table_name='doctors')
    op.drop_table('doctors')
    op.drop_index(op.f('ix_analytics_snapshot_date'), table_name='analytics')
    op.drop_index(op.f('ix_analytics_created_at'), table_name='analytics')
    op.drop_table('analytics')
    # ### end Alembic commands ###
    op.execute("DROP SEQUENCE IF EXISTS queue_number_seq")
    # Postgres ENUM types outlive the tables that use them; Alembic does not
    # drop them automatically, which makes a downgrade/upgrade cycle fail with
    # "type already exists".
    for enum_name in ("urgencylevel", "queuestatus", "smsstatus"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
