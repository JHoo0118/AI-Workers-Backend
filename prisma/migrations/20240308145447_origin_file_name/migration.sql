/*
  Warnings:

  - Added the required column `originFileName` to the `File` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "File" ADD COLUMN     "originFileName" TEXT NOT NULL;
