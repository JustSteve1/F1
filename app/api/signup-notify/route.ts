import { NextResponse } from 'next/server';
import nodemailer from 'nodemailer';

export async function POST(request: Request) {
    try {
        const { name, email } = await request.json();

        // CRM/Notification Email (To You)
        const transporter = nodemailer.createTransport({
            service: 'gmail',
            auth: {
                user: process.env.EMAIL_USER,
                pass: process.env.EMAIL_PASS,
            },
        });

        const mailOptions = {
            from: process.env.EMAIL_USER,
            to: 'mrstevefortuin@gmail.com',
            subject: `Sign-up: ${name}`,
            text: `New user signed up:\n\nName: ${name}\nEmail: ${email}\n\nCheck Firebase Console for more details.`,
        };

        await transporter.sendMail(mailOptions);

        return NextResponse.json({ message: 'Email sent successfully' }, { status: 200 });
    } catch (error) {
        console.error('Failed to send email:', error);
        return NextResponse.json({ error: 'Failed to send email' }, { status: 500 });
    }
}
