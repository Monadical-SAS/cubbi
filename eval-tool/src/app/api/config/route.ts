import { NextRequest, NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { ConfigData } from '@/app/types';

export async function POST(request: NextRequest) {
  try {
    // Parse the request body
    const data: ConfigData = await request.json();
    
    // Validate the data
    if (!data || !data.containers || !data.exercises || !data.output_dir) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Create uploads directory in the public folder if it doesn't exist
    const uploadsDir = path.join(process.cwd(), 'public', 'uploads');
    try {
      await fs.access(uploadsDir);
    } catch {
      await fs.mkdir(uploadsDir, { recursive: true });
    }

    // Create a unique filename based on timestamp and first container name
    const timestamp = new Date().toISOString().replace(/[:.-]/g, '_');
    const firstContainerName = data.containers[0]?.name || 'config';
    const sanitizedName = firstContainerName.replace(/[^a-zA-Z0-9_-]/g, '_');
    const filename = `${sanitizedName}_${timestamp}.json`;
    const filePath = path.join(uploadsDir, filename);

    // Write the data to the file
    await fs.writeFile(filePath, JSON.stringify(data, null, 2), 'utf8');

    return NextResponse.json({ 
      success: true, 
      message: 'Configuration saved successfully',
      filename, 
      path: `/uploads/${filename}`
    });
  } catch (error) {
    console.error('Error saving configuration:', error);
    return NextResponse.json(
      { error: 'Failed to save configuration' },
      { status: 500 }
    );
  }
}