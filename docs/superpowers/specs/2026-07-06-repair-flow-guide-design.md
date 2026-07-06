# Repair Flow Guide Design

## Goal

The main diagnostic page should guide overseas technicians through a standard mainboard repair workflow instead of exposing knowledge-base construction details.

## Primary User

Overseas local technicians who need step-by-step guidance for mainboard troubleshooting.

## UX Principle

The page should answer one question at a time: what should the technician do now?

Do not show developer/project-building information in the primary flow, such as SOP source, data gaps, evidence summaries, or knowledge-base readiness scores.

## Flow

1. Fault intake
2. Basic exclusion
3. Test and locate
4. Repair or escalate
5. Verify and record

## Visual Hierarchy

The current step is the visual center. It uses a large dark-blue task area with one primary action.

The right side is auxiliary only. It shows the current or next measurement location and the fields that need to be recorded for the current step.

The top stepper provides orientation but should not compete with the main task.

## Current Scope

This iteration implements the main diagnostic flow page only. Secondary pages such as model library, repair steps, SN/Log tools, and records remain accessible but are not redesigned yet.

## Validation

The page must pass desktop and mobile visual checks, key step clicks, query input, model/fault matching, and console-error checks.
