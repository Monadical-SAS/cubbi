import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';

export async function GET() {
  try {
    // Get the uploads directory
    const uploadsDir = path.join(process.cwd(), 'public', 'uploads');
    
    try {
      await fs.access(uploadsDir);
    } catch {
      // Create directory if it doesn't exist
      await fs.mkdir(uploadsDir, { recursive: true });
      // Return empty array if directory was just created
      return NextResponse.json({ configs: [] });
    }
    
    // Read all files in the directory
    const files = await fs.readdir(uploadsDir);
    
    // Filter for JSON files
    const jsonFiles = files.filter(file => file.endsWith('.json'));
    
    // Get file stats to sort by modified time
    const fileStats = await Promise.all(
      jsonFiles.map(async (file) => {
        const filePath = path.join(uploadsDir, file);
        const stats = await fs.stat(filePath);
        return {
          filename: file,
          path: `/uploads/${file}`,
          lastModified: stats.mtime.toISOString(),
          size: stats.size
        };
      })
    );
    
    // Sort files by modification time (newest first)
    const sortedFiles = fileStats.sort((a, b) => 
      new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime()
    );
    
    return NextResponse.json({ configs: sortedFiles });
  } catch (error) {
    console.error('Error fetching configurations:', error);
    return NextResponse.json(
      { error: 'Failed to fetch configurations' },
      { status: 500 }
    );
  }
}